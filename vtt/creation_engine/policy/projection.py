"""One allowlisted projection for reads, explanations, exports and delivery.

Document builders and reviewed declassifications are trusted host registrations.
Unlabelled/raw engine dictionaries cannot enter this boundary. Source labels must
cover the entire value, including nested data and every calculation dependency.
"""

from dataclasses import dataclass

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.contracts import validate_definition
from .rules import Principal
from .public_errors import safe_code


@dataclass(frozen=True)
class Source:
    policy_id: str
    category: str


@dataclass(frozen=True)
class Field:
    value: object
    policy_id: str
    sources: tuple[Source, ...] = ()
    declassification_id: str | None = None
    content_digest: bool = False


@dataclass(frozen=True)
class Document:
    id: str
    policy_id: str
    fields: dict[str, Field]
    children: tuple["Document", ...] = ()
    manual: bool = False
    required_policies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Declassification:
    id: str
    output_fields: frozenset[str]
    input_categories: frozenset[str]
    audience: tuple  # explicit Grant selectors, one per allowed output operation

    def wire(self):
        return {"id": self.id, "outputFields": sorted(self.output_fields),
                "inputCategories": sorted(self.input_categories), "audience": [g.wire() for g in self.audience]}


def project(document, policies, audience, *, operation="read", declassifications=()):
    if not isinstance(document, Document):
        raise TypeError("projection requires a labelled Document")
    # Read permission is also required for exports and explanations.
    def allowed(policy_id):
        return policies.allows_audience(audience, policy_id, "read") and policies.allows_audience(audience, policy_id, operation)
    if not allowed(document.policy_id) or any(not allowed(policy) for policy in document.required_policies):
        return None
    rules = {rule.id: rule for rule in declassifications}
    fields = {}
    for name, field in document.fields.items():
        if not isinstance(field, Field):
            raise TypeError("projection fields require source labels")
        if not allowed(field.policy_id):
            continue
        if any(not policies.allows(Principal(0, frozenset({"engine"})), s.policy_id, "compute") for s in field.sources):
            continue
        disclosed = all(allowed(source.policy_id) for source in field.sources)
        if not disclosed:
            rule = rules.get(field.declassification_id)
            disclosed = bool(not field.content_digest and rule and name in rule.output_fields
                and {s.category for s in field.sources} <= rule.input_categories
                and all(any(g.matches(p, operation) for g in rule.audience) for p in audience))
        if disclosed:
            # Return independent JSON values; a caller cannot contaminate a cache.
            fields[name] = parse_strict_json(canonical_bytes(field.value))
    children = [value for child in document.children
                if (value := project(child, policies, audience, operation=operation,
                                     declassifications=declassifications)) is not None]
    result = {"id": document.id, "fields": fields, "children": children}
    if document.manual:
        result.update(manual=True, automatedCompletion=False)
    return result


def public_receipt(internal, *, visible_event_ids, checkpoint_visible=False):
    keys = ("commandId", "operationId", "requestDigest", "status", "scopeId", "stateVersion", "authorityEpoch", "errorCode")
    result = {key: internal[key] for key in keys}
    result["errorCode"] = safe_code(result["errorCode"])
    result["checkpointId"] = internal["checkpointId"] if checkpoint_visible else None
    allowed = set(visible_event_ids)
    result["eventIds"] = [event for event in internal["eventIds"] if event in allowed]
    validate_definition("PublicReceipt", result)
    return result


def cache_key(*, audience, scope_id, policy_epoch, access_stamp, state_version, lock_digest,
              representation_version, object_id, operation):
    """Internal cache identity. Never publish this hash or an ETag over hidden data."""
    return content_digest({"audience": [{"id": p.id, "roles": sorted(p.roles), "entitlement": p.entitlement_epoch,
                                        "entitlements": sorted(p.entitlements)}
                                       for p in audience],
        "scope": scope_id, "policy": policy_epoch, "access": access_stamp, "state": state_version,
        "lock": lock_digest, "representation": representation_version, "object": object_id, "operation": operation})
