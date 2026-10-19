"""Legacy presentation and write translation into the approved command envelopes."""

from sqlalchemy.orm import Session

from vtt.creation_engine.adapter.mapping import BINDINGS, RESOURCES
from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.migration_models import CeRepresentation
from vtt.creation_engine.store.runtime_models import CeCheckpoint, CeRuntimeScope
from vtt.creation_engine.types import parse_id

FIELD_BINDINGS = {column.removesuffix("_score"): binding for column, binding in BINDINGS.items()}


class LegacyCompatibility:
    def __init__(self, gateway):
        self.gateway = gateway

    def representation(self, kind, source_id):
        with Session(self.gateway.store.engine) as session:
            row = session.get(CeRepresentation, (kind, source_id))
            if row is None:
                return None
            scope = session.get(CeRuntimeScope, row.scope_id)
            if scope.migration_state != "ENGINE":
                return None
            return {"scopeId": row.scope_id, "instanceId": row.instance_id,
                    "authorityEpoch": scope.authority_epoch, "stateVersion": scope.state_version}

    def read(self, principal, kind, source_id, *, operation="read", view_id=None):
        ref = self.representation(kind, source_id)
        if ref is None:
            return None
        with self.gateway._transaction(ref["scopeId"]) as tx:
            audience = self.gateway._audience(tx, principal, view_id)
            if kind == "vtt.token":
                from vtt.models.token_state import TokenState
                token = tx.session.get(TokenState, source_id)
                if token is None or token.deleted_at or token.campaign_id != tx.scope.campaign_id:
                    refuse("NOT_FOUND")
                for viewer in audience:
                    if (token.visibility != "public" and "operator" not in viewer.roles
                            and not (token.visibility == "owner_only" and token.owner_user_id == viewer.id)):
                        refuse("NOT_FOUND")
            document = self.gateway.document(tx, ref["instanceId"])
            projected = self.gateway._project(tx, audience, document, operation)
            if projected is None:
                refuse("NOT_FOUND")
            return {"id": source_id, **projected["fields"], "engine": {
                "scopeId": tx.scope.id, "instanceId": ref["instanceId"], "authorityEpoch": tx.scope.authority_epoch,
                "stateVersion": tx.scope.state_version, "executionLockDigest": tx.lock.digest},
                "manual": projected.get("manual", False), "items": projected["children"]}

    def translate(self, principal, kind, source_id, changes, context, *, delta=False, reason="legacy sheet edit"):
        """One explicit legacy field per command; mixed writes cannot partly commit.

        Absolute-resource retries reconstruct the original delta from the retained
        checkpoint, never from the resource's changed current value.
        """
        ref = self.representation(kind, source_id)
        if ref is None:
            return None
        if not isinstance(context, dict):
            refuse("SCHEMA_INVALID")
        if not isinstance(changes, dict) or len(changes) != 1:
            refuse("LEGACY_FIELD_READ_ONLY", "submit each supported input as an explicit engine command")
        field, value = next(iter(changes.items()))
        if field == "campaign_id":
            refuse("SCOPE_TRANSFER_UNSUPPORTED")
        if field not in FIELD_BINDINGS and field not in RESOURCES and field != "is_equipped":
            refuse("LEGACY_FIELD_READ_ONLY")
        if type(context.get("authorityEpoch")) is not int:
            refuse("AUTHORITY_EPOCH_MISMATCH")
        if type(context.get("expectedScopeVersion")) is not int:
            refuse("SCOPE_VERSION_CONFLICT")
        key = parse_id(context.get("idempotencyKey"))
        with self.gateway.store.transaction(ref["scopeId"]) as tx:
            self.gateway.policy.require_scope(tx, principal)
            if context["authorityEpoch"] != tx.scope.authority_epoch:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            instance = {"kind": "instance", "id": ref["instanceId"], "scopeId": tx.scope.id}
            if field == "is_equipped":
                if type(value) is not bool or kind != "vtt.equipment":
                    refuse("SCHEMA_INVALID")
                operation, payload = "SetItemEquipped", {"item": instance, "equipped": value}
            else:
                if type(value) is not int or abs(value) > 2**53 - 1:
                    refuse("SCHEMA_INVALID")
                if field in RESOURCES:
                    resource_id = RESOURCES[field]
                    resource = tx.resource(instance["id"], resource_id)
                    before = resource["current"]
                    prior = tx.receipt(principal, key)
                    if prior and prior["checkpointId"]:
                        checkpoint = tx.session.get(CeCheckpoint, prior["checkpointId"])
                        for change in parse_strict_json(checkpoint.outcome).get("changes", []):
                            if (change["instanceId"], change["resourceId"]) == (instance["id"], resource_id):
                                before = Rational.from_wire(change["before"])
                    amount = Rational.of(value) if delta else Rational.of(value) - before
                    operation, payload = "AdjustResource", {"instance": instance, "resourceId": resource_id,
                        "delta": {"value": amount.to_wire(), "unit": resource["unit"]}, "reason": reason}
                else:
                    binding = FIELD_BINDINGS[field]
                    operation = "SetBaseValue" if field in {"str", "dex", "con", "int", "wis", "cha"} else "SetValueOverride"
                    payload = {"instance": instance, "bindingId": binding, "reason": reason,
                        "value": {"value": Rational.of(value).to_wire(), "unit": self.gateway.kernel.ruleset.binding(binding).unit}}
            wire = {"contractVersion": "1.1.3", "commandId": new_id("cmd"), "idempotencyKey": key,
                "scopeId": tx.scope.id, "authorityEpoch": context["authorityEpoch"],
                "expectedScopeVersion": context["expectedScopeVersion"], "executionLockDigest": tx.lock.digest,
                "operation": operation, "payload": payload}
        return self.gateway.submit(principal, canonical_bytes(wire))
