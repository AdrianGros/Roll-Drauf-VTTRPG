"""Current PostgreSQL authorization under the runtime scope lock.

Only trusted installation and policy-writer code calls bootstrap/replace. There
is deliberately no unregistered public grant command. Content never grants rights.
"""

from datetime import timedelta
import secrets

from sqlalchemy import select, update

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.types import parse_id
from vtt.creation_engine.policy import Grant, Policy, PolicySet, Principal
from vtt.creation_engine.store.policy_models import (CePolicy, CePolicyEpoch, CeSecurityAudit,
                                                     CeSubscription, CeViewAsSession)
from vtt.creation_engine.store.runtime_models import CeInstance
from vtt.models.campaign import Campaign
from vtt.models.campaign_member import CampaignMember


def nonce(prefix):
    return prefix + ":" + secrets.token_urlsafe(32)


class PolicyStore:
    def principal(self, tx, principal_id):
        tx.require_usable_account(principal_id)
        roles = set()
        if tx.scope.kind == "sandbox":
            if principal_id == tx.scope.owner_user_id:
                roles.update(("member", "operator", "owner"))
        else:
            campaign = tx.session.scalar(select(Campaign).where(Campaign.id == tx.scope.campaign_id)
                                         .with_for_update(read=True))
            member = tx.session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == tx.scope.campaign_id,
                                    CampaignMember.user_id == principal_id).with_for_update(read=True))
            if campaign and campaign.status == "active" and campaign.deleted_at is None:
                if campaign.owner_id == principal_id:
                    roles.update(("member", "operator", "owner"))
                elif member and member.status == "active":
                    roles.add("member")
                    if member.is_operator():
                        roles.add("operator")
        epoch = tx.session.get(CePolicyEpoch, (tx.scope.id, principal_id))
        entitlements = frozenset(parse_strict_json(epoch.entitlements)) if epoch and (
            epoch.valid_until is None or tx.now < epoch.valid_until) else frozenset()
        return Principal(principal_id, frozenset(roles), epoch.entitlement_epoch if epoch else 0, entitlements)

    def policies(self, tx):
        rows = tx.session.scalars(select(CePolicy).where(CePolicy.scope_id == tx.scope.id)
                                 .order_by(CePolicy.policy_id, CePolicy.version.desc()))
        current = {}
        for row in rows:
            current.setdefault(row.policy_id, Policy.restore(parse_strict_json(row.canonical)))
        return PolicySet(tx.scope.id, current.values())

    def require_scope(self, tx, principal_id):
        principal = self.principal(tx, principal_id)
        if (tx.scope.kind == "campaign" and "member" not in principal.roles) or not self.policies(tx).allows(principal, tx.scope.id):
            refuse("NOT_FOUND")
        return principal

    def audit(self, tx, principal_id, kind, details):
        tx.session.add(CeSecurityAudit(id=new_id("audit"), scope_id=tx.scope.id, principal_id=principal_id,
            kind=kind, canonical=canonical_bytes(details), created_at=tx.now))

    def bootstrap(self, tx, principal_id):
        """Install spec §5's default grants, only for an unconfigured owned scope."""
        tx.require_usable_account(principal_id)
        if principal_id != tx.scope.owner_user_id or self.policies(tx).policies:
            refuse("OPERATION_FORBIDDEN")
        root = Policy(tx.scope.id, None, tuple(Grant(op, roles=("member",)) for op in
            ("read", "explain", "export", "controls", "invoke", "adjust", "respond")) +
            tuple(Grant(op, roles=("operator",)) for op in ("operates", "view_as", "policy_admin", "audit")) +
            (Grant("compute", roles=("engine",)),))
        policies = [root]
        for instance in tx.session.scalars(select(CeInstance).where(CeInstance.scope_id == tx.scope.id)):
            controller = tx.scope.owner_user_id if tx.scope.kind == "sandbox" else instance.controller_user_id
            policies.append(Policy(instance.id, root.id,
                tuple(Grant(op, principals=(controller,)) for op in
                      ("read", "explain", "export", "controls", "invoke", "adjust", "respond")) +
                (Grant("compute", roles=("engine",)),)))
        for policy in policies:
            tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=policy.id, version=tx.scope.policy_version,
                                    canonical=canonical_bytes(policy.wire())))
        self.audit(tx, principal_id, "policy_bootstrap", {"policies": [p.id for p in policies]})
        tx.session.flush()

    def replace(self, tx, kernel, principal_id, policy, *, expected_version, reason):
        principal, policies = self.require_scope(tx, principal_id), self.policies(tx)
        old = policies.policies.get(policy.id)
        own_private = old is not None and old.owner_id == principal_id == policy.owner_id and old.parent_id == policy.parent_id
        if not own_private and not policies.allows(principal, tx.scope.id, "policy_admin"):
            refuse("OPERATION_FORBIDDEN")
        if tx.scope.policy_version != expected_version:
            refuse("POLICY_VERSION_CONFLICT")
        # Operators cannot create their own grant to somebody else's private data.
        if old and old.owner_id is not None and old.owner_id != principal_id:
            if not any(g.matches(principal, "policy_admin") for g in old.owner_grants):
                refuse("OPERATION_FORBIDDEN")
        if policy.owner_id is not None and policy.owner_id != principal_id and (old is None or old.owner_id != policy.owner_id):
            refuse("OPERATION_FORBIDDEN")
        proposed = PolicySet(tx.scope.id, [p for p in policies.policies.values() if p.id != policy.id] + [policy])
        if any(not proposed.chain(p.id) for p in proposed.policies.values()):
            refuse("SEMANTIC_INVALID", "policy has a missing parent or cycle")
        self.changed(tx, kernel, principal_id, reason=reason)
        tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=policy.id, version=tx.scope.policy_version,
                               canonical=canonical_bytes(policy.wire())))
        self.audit(tx, principal_id, "policy_replaced", {"policyId": policy.id, "version": tx.scope.policy_version, "reason": reason})
        tx.session.flush()

    def changed(self, tx, kernel, principal_id, *, reason, entitlement_principal=None, entitlements=None, valid_until=None):
        """Trusted membership/entitlement writer hook; same transaction as the change."""
        if entitlements is not None:
            if entitlement_principal is None or len(entitlements) > 128:
                refuse("SEMANTIC_INVALID")
            for entitlement in entitlements:
                parse_id(entitlement)
        kernel.policy_changed(tx, reason=reason)
        if entitlement_principal is not None:
            row = tx.session.get(CePolicyEpoch, (tx.scope.id, entitlement_principal))
            if row is None:
                row = CePolicyEpoch(scope_id=tx.scope.id, principal_id=entitlement_principal, entitlement_epoch=0, entitlements=b"[]")
                tx.session.add(row)
            row.entitlement_epoch += 1
            if entitlements is not None:
                row.entitlements, row.valid_until = canonical_bytes(sorted(set(entitlements))), valid_until
        tx.session.execute(update(CeSubscription).where(CeSubscription.scope_id == tx.scope.id,
            CeSubscription.revoked_at.is_(None)).values(revoked_at=tx.now))
        for view in tx.session.scalars(select(CeViewAsSession).where(CeViewAsSession.scope_id == tx.scope.id,
                                                                   CeViewAsSession.closed_at.is_(None))):
            self.close_view(tx, view.operator_id, view.id, reason="policy_changed")
        self.audit(tx, principal_id, "policy_changed", {"reason": reason, "policyVersion": tx.scope.policy_version})

    def access_stamp(self, audience):
        return content_digest([{"id": p.id, "roles": sorted(p.roles), "entitlement": p.entitlement_epoch,
                                "entitlements": sorted(p.entitlements)} for p in audience])

    def audience(self, tx, principal_id, view_id=None):
        principal = self.require_scope(tx, principal_id)
        if view_id is None:
            return (principal,)
        parse_id(view_id)
        view = tx.session.get(CeViewAsSession, view_id)
        if view is None or view.scope_id != tx.scope.id or view.operator_id != principal_id:
            refuse("NOT_FOUND")
        if view.closed_at is not None or tx.now >= view.expires_at or view.policy_epoch != tx.scope.policy_version:
            refuse("OPERATION_FORBIDDEN")
        if not all(self.policies(tx).allows(principal, tx.scope.id, op) for op in ("view_as", "operates")):
            refuse("OPERATION_FORBIDDEN")
        audience = (principal, self.require_scope(tx, view.member_id))
        if self.access_stamp(audience) != view.access_stamp:
            refuse("OPERATION_FORBIDDEN")
        return audience

    def enter_view(self, tx, principal_id, member_id):
        operator = self.require_scope(tx, principal_id)
        if not all(self.policies(tx).allows(operator, tx.scope.id, op) for op in ("view_as", "operates")):
            refuse("OPERATION_FORBIDDEN")
        member = self.require_scope(tx, member_id)
        view = CeViewAsSession(id=nonce("view"), scope_id=tx.scope.id, operator_id=principal_id, member_id=member_id,
            access_stamp=self.access_stamp((operator, member)), policy_epoch=tx.scope.policy_version,
            expires_at=tx.now + timedelta(minutes=15))
        tx.session.add(view)
        self.audit(tx, principal_id, "view_as_entered", {"sessionId": view.id, "memberId": member_id})
        return {"viewAsId": view.id, "operatorId": principal_id, "memberId": member_id,
                "expiresAt": view.expires_at.isoformat().replace("+00:00", "Z"), "readOnly": True}

    def close_view(self, tx, principal_id, view_id, *, reason="exit"):
        view = tx.session.get(CeViewAsSession, view_id)
        if view is None or view.scope_id != tx.scope.id or view.operator_id != principal_id:
            refuse("NOT_FOUND")
        if view.closed_at is None:
            view.closed_at = tx.now
            self.audit(tx, principal_id, "view_as_exited", {"sessionId": view.id, "memberId": view.member_id, "reason": reason})

    def expire_views(self, tx):
        for view in tx.session.scalars(select(CeViewAsSession).where(CeViewAsSession.scope_id == tx.scope.id,
                CeViewAsSession.closed_at.is_(None), CeViewAsSession.expires_at <= tx.now)):
            self.close_view(tx, view.operator_id, view.id, reason="expired")

    def authorize(self, tx, principal_id, wire):
        principal, policies = self.require_scope(tx, principal_id), self.policies(tx)
        op, payload = wire["operation"], wire["payload"]
        def visible(ref):
            instance = tx.instance(ref)
            if not policies.allows(principal, instance.id):
                refuse("NOT_FOUND")
            return instance.id
        if op == "InvokeActivity":
            actor, source = visible(payload["actorInstance"]), visible(payload["sourceInstance"])
            for target in payload["targets"]:
                visible(target)
            return policies.allows(principal, actor, "controls") and policies.allows(principal, actor, "invoke") and policies.allows(principal, source, "invoke")
        if op == "AdjustResource":
            target = visible(payload["instance"])
            return policies.allows(principal, target, "controls") and policies.allows(principal, target, "adjust")
        if op == "ResolveDecision":
            decision = tx.decision(payload["decisionId"], payload["expectedDecisionVersion"])
            if not policies.allows(principal, decision.question.policy_id):
                refuse("NOT_FOUND")
            return policies.allows(principal, decision.question.policy_id, "respond")
        if op in {"ReissueDecision", "ReassignDecisionResponder", "ResumeSuspendedAction", "ResolveActionManually"}:
            if not policies.allows(principal, tx.scope.id, "operates"):
                refuse("NOT_FOUND")
            tx.action(payload["actionId"])
            return True
        return False

    def authorize_operator(self, tx, principal_id, wire):
        return self.policies(tx).allows(self.require_scope(tx, principal_id), tx.scope.id, "operates")
