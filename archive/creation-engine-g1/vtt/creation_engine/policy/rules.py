"""Explicit grants, prevailing denies and intersected container restrictions.

Roles come from the authenticated host, never content or a command envelope.
Policies are mutable security overlays, independent of immutable revisions.
"""

from dataclasses import dataclass

from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.types import parse_id

OPERATIONS = frozenset({"read", "explain", "export", "compute", "controls", "operates", "invoke",
                        "adjust", "respond", "view_as", "policy_admin", "audit", "deploy"})


@dataclass(frozen=True)
class Principal:
    id: int
    roles: frozenset[str]
    entitlement_epoch: int = 0
    entitlements: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Grant:
    operation: str
    principals: tuple[int, ...] = ()
    roles: tuple[str, ...] = ()

    def __post_init__(self):
        if self.operation not in OPERATIONS or any(type(p) is not int or p <= 0 for p in self.principals):
            refuse("SEMANTIC_INVALID", "invalid policy grant")
        if len(self.principals) + len(self.roles) > 128 or any(not isinstance(r, str) for r in self.roles):
            refuse("SEMANTIC_INVALID", "invalid policy selectors")
        for role in self.roles:
            parse_id(role)

    def matches(self, principal, operation):
        return self.operation == operation and (principal.id in self.principals or bool(principal.roles.intersection(self.roles)))

    def wire(self):
        return {"operation": self.operation, "principals": list(self.principals), "roles": list(self.roles)}


@dataclass(frozen=True)
class Policy:
    id: str
    parent_id: str | None
    grants: tuple[Grant, ...] = ()
    denies: tuple[Grant, ...] = ()
    owner_id: int | None = None
    owner_grants: tuple[Grant, ...] = ()
    required_entitlements: tuple[str, ...] = ()

    def __post_init__(self):
        parse_id(self.id)
        if self.parent_id is not None:
            parse_id(self.parent_id)
        if self.owner_id is not None and (type(self.owner_id) is not int or self.owner_id <= 0):
            refuse("SEMANTIC_INVALID", "invalid private owner")
        if len(self.grants) + len(self.denies) + len(self.owner_grants) > 256:
            refuse("SEMANTIC_INVALID", "policy exceeds grant limit")
        if len(self.required_entitlements) > 128:
            refuse("SEMANTIC_INVALID", "policy exceeds entitlement limit")
        for entitlement in self.required_entitlements:
            parse_id(entitlement)

    def wire(self):
        return {"id": self.id, "parent_id": self.parent_id, "owner_id": self.owner_id,
                "grants": [g.wire() for g in self.grants], "denies": [g.wire() for g in self.denies],
                "owner_grants": [g.wire() for g in self.owner_grants], "required_entitlements": list(self.required_entitlements)}

    @classmethod
    def restore(cls, value):
        def grants(key):
            return tuple(Grant(g["operation"], tuple(g["principals"]), tuple(g["roles"])) for g in value[key])
        return cls(value["id"], value["parent_id"], grants("grants"), grants("denies"), value["owner_id"],
                   grants("owner_grants"), tuple(value.get("required_entitlements", ())))


class PolicySet:
    def __init__(self, root_id, policies):
        self.root_id = root_id
        self.policies = {p.id: p for p in policies}

    def chain(self, policy_id):
        result, seen = [], set()
        while policy_id is not None:
            if policy_id in seen or len(seen) >= 32 or policy_id not in self.policies:
                return ()
            seen.add(policy_id)
            policy = self.policies[policy_id]
            result.append(policy)
            policy_id = policy.parent_id
        return tuple(result) if result and result[-1].id == self.root_id else ()

    def allows(self, principal, policy_id, operation="read"):
        chain = self.chain(policy_id)
        if not chain or operation not in OPERATIONS:
            return False
        for policy in chain:
            # Engine computation has its own explicit grant. Client read/export
            # entitlements cannot be inferred from that server-only capability.
            if operation != "compute" and not set(policy.required_entitlements) <= principal.entitlements:
                return False
            if any(g.matches(principal, operation) for g in policy.denies):
                return False
            if not any(g.matches(principal, operation) for g in policy.grants):
                return False
            if policy.owner_id is not None and principal.id != policy.owner_id:
                if not any(g.matches(principal, operation) for g in policy.owner_grants):
                    return False
        return True

    def allows_audience(self, audience, policy_id, operation="read"):
        return bool(audience) and all(self.allows(p, policy_id, operation) for p in audience)
