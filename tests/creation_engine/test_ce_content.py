"""WP3 domain: schema registry, rulesets, immutable revisions, drafts and execution locks (spec v1.1.4 §4, §6, §12)."""

import hashlib
from datetime import UTC, datetime

import pytest

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.content import (AdjustBoundPolicy, BindingTemplate, Draft, ResourceSpec, Ruleset, SchemaRegistry,
                                         SchemaType, SchemaTypeRef, create_revision, require_draft_version, resolve_lock)
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.errors import DRAFT_VERSION_CONFLICT, SCHEMA_INVALID, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.evaluator import Rounding
from vtt.creation_engine.evaluator.identity import EVALUATOR_VERSION, evaluator_artifact
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import RevisionRef
from vtt.creation_engine.units import DIMENSIONLESS, Unit, UnitTable

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
CORE = "urn:rolldrauf:creation-engine:contracts:1.1.3#/$defs/"
ITEM = SchemaTypeRef("test.item", 1)


def _no_forbidden_names(content):
    if content["name"] == "forbidden":
        raise ContractViolation(SEMANTIC_INVALID, "name is reserved")


ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "bonus": {"$ref": CORE + "Quantity"},
        "uses": {"type": "array", "items": {"$ref": CORE + "RevisionRef"}, "maxItems": 16},
    },
    "required": ["name"],
    "additionalProperties": False,
}
REGISTRY = SchemaRegistry("ce.test-bundle", "1", [SchemaType("test.item", 1, ITEM_SCHEMA, _no_forbidden_names)])
UNITS = UnitTable([Unit("unit:dimensionless", DIMENSIONLESS, Rational.of(1)), Unit("unit:point", "dimension:score", Rational.of(1)),
                   Unit("unit:hp", "dimension:hp", Rational.of(1))])
RULESET = Ruleset("rules.test", "0.1.0", UNITS,
                  bindings=(BindingTemplate("defense", "unit:point", Rounding.FLOOR, overrideable=True),
                            BindingTemplate("hp_max", "unit:hp", Rounding.FLOOR)),
                  resources=(ResourceSpec("hp", "unit:hp", "hp_max", AdjustBoundPolicy.CLAMP_REPORT_DELTA),))


def revision(definition_id="def:sword", content=None, **kwargs):
    return create_revision(definition_id, ITEM, content or {"name": "Flame sword"}, registry=REGISTRY, author_user_id=1,
                           provenance={"source": "test"}, now=NOW, **kwargs)


# --- schema registry (§6) --------------------------------------------------------------------------

def test_content_is_validated_by_schema_then_semantics():
    REGISTRY.validate(ITEM, {"name": "Flame sword", "bonus": {"value": {"numerator": 1, "denominator": 1}, "unit": "unit:point"}})
    with pytest.raises(ContractViolation) as unknown_field:
        REGISTRY.validate(ITEM, {"name": "x", "damage": 3})
    assert unknown_field.value.code == SCHEMA_INVALID
    with pytest.raises(ContractViolation) as semantic:
        REGISTRY.validate(ITEM, {"name": "forbidden"})
    assert semantic.value.code == SEMANTIC_INVALID


def test_unsupported_schema_versions_are_rejected():
    with pytest.raises(ContractViolation) as caught:
        REGISTRY.validate(SchemaTypeRef("test.item", 2), {"name": "x"})
    assert caught.value.code == SEMANTIC_INVALID


def test_schema_bundle_digest_pins_every_schema():
    changed = SchemaRegistry("ce.test-bundle", "1", [SchemaType("test.item", 1, {**ITEM_SCHEMA, "required": []})])
    assert REGISTRY.artifact()["digest"] != changed.artifact()["digest"]
    assert REGISTRY.artifact() == SchemaRegistry("ce.test-bundle", "1", [SchemaType("test.item", 1, ITEM_SCHEMA)]).artifact()


# --- rulesets --------------------------------------------------------------------------------------

@pytest.mark.parametrize("bindings, resources", [
    ((BindingTemplate("defense", "unit:parsec", None),), ()),                                          # unknown unit
    ((BindingTemplate("defense", "unit:point", None), BindingTemplate("defense", "unit:point", None)), ()),
    ((BindingTemplate("defense", "unit:point", None),),
     (ResourceSpec("hp", "unit:hp", "defense", AdjustBoundPolicy.REJECT),)),                          # max of another dimension
])
def test_invalid_rulesets_are_rejected(bindings, resources):
    with pytest.raises(ContractViolation) as caught:
        Ruleset("rules.bad", "1", UNITS, bindings, resources)
    assert caught.value.code == SEMANTIC_INVALID


def test_ruleset_artifact_changes_with_any_declaration():
    stricter = Ruleset("rules.test", "0.1.0", UNITS, RULESET.bindings,
                       (ResourceSpec("hp", "unit:hp", "hp_max", AdjustBoundPolicy.REJECT),))
    assert RULESET.artifact()["digest"] != stricter.artifact()["digest"]


# --- revisions (§4, §6) ----------------------------------------------------------------------------

def test_revision_digest_identifies_canonical_bytes_regardless_of_key_order():
    content = {"name": "Flame sword", "bonus": {"unit": "unit:point", "value": {"denominator": 1, "numerator": 2}}}
    first, second = revision(content=content), revision(content=dict(reversed(list(content.items()))))
    assert first.digest == second.digest == "sha256:" + hashlib.sha256(canonical_bytes(content)).hexdigest()
    assert first.id != second.id                       # a new revision is a new identity, even with equal content


def test_revision_content_cannot_be_altered_through_its_accessor():
    frozen = revision()
    frozen.content["name"] = "Tampered"
    assert frozen.content["name"] == "Flame sword"


def test_revision_dependencies_are_the_tagged_revision_references():
    dependency = revision("def:fire")
    item = revision(content={"name": "Flame sword", "uses": [dependency.ref().to_wire()]})
    assert item.dependencies() == (dependency.ref(),)


# --- drafts (§13, §15) -----------------------------------------------------------------------------

def test_stale_draft_versions_conflict():
    draft = Draft("draft:1", "ws:1", None, ITEM, "de", 3, b"{}", NOW, NOW, canonical_bytes(REGISTRY.artifact()))
    require_draft_version(draft, 3)
    with pytest.raises(ContractViolation) as caught:
        require_draft_version(draft, 2)
    assert caught.value.code == DRAFT_VERSION_CONFLICT


# --- execution locks (§12) -------------------------------------------------------------------------

def _lock(revisions, roots, configuration=None):
    by_id = {r.id: r for r in revisions}
    return resolve_lock(roots, fetch=by_id.get, ruleset=RULESET, registry=REGISTRY, evaluator=evaluator_artifact(),
                        configuration=configuration or {"campaign": "test"})


def test_lock_pins_the_transitive_closure_and_every_artifact():
    fire = revision("def:fire")
    sword = revision(content={"name": "Flame sword", "uses": [fire.ref().to_wire()]})
    lock = _lock([fire, sword], [sword.ref()])
    validate_definition("ExecutionLock", lock.wire)
    assert set(lock.revisions) == {fire.ref(), sword.ref()}
    assert lock.wire["ruleset"] == RULESET.artifact()
    assert lock.wire["schemaBundle"] == REGISTRY.artifact()
    assert lock.wire["unitTableDigest"] == UNITS.digest()
    assert lock.wire["evaluator"] == evaluator_artifact()


def test_same_closure_gives_the_same_lock():
    fire, ring = revision("def:fire"), revision("def:ring")
    assert _lock([fire, ring], [fire.ref(), ring.ref()]) == _lock([fire, ring], [ring.ref(), fire.ref()])
    assert _lock([fire], [fire.ref()]).lock_id != _lock([fire], [fire.ref()], {"campaign": "other"}).lock_id


def test_missing_dependency_is_rejected():
    fire = revision("def:fire")
    sword = revision(content={"name": "Flame sword", "uses": [fire.ref().to_wire()]})
    with pytest.raises(ContractViolation, match="missing dependency"):
        _lock([sword], [sword.ref()])


def test_digest_mismatch_is_rejected():
    fire = revision("def:fire")
    forged = RevisionRef(fire.id, fire.definition_id, "sha256:" + "f" * 64)
    with pytest.raises(ContractViolation, match="digest mismatch"):
        _lock([fire], [forged])


def test_two_revisions_of_one_definition_are_ambiguous():
    old, new = revision("def:fire"), revision("def:fire", content={"name": "Fire v2"})
    with pytest.raises(ContractViolation, match="ambiguous identity"):
        _lock([old, new], [old.ref(), new.ref()])


def test_revisions_of_unsupported_types_cannot_be_locked():
    stray = create_revision("def:x", ITEM, {"name": "x"}, registry=REGISTRY, author_user_id=1, provenance={}, now=NOW)
    other_registry = SchemaRegistry("ce.other", "1", [])
    with pytest.raises(ContractViolation, match="not supported"):
        resolve_lock([stray.ref()], fetch={stray.id: stray}.get, ruleset=RULESET, registry=other_registry,
                     evaluator=evaluator_artifact(), configuration={})


@pytest.mark.parametrize('change', [{'id': 'unsupported.engine'}, {'version': '99'}, {'digest': 'sha256:' + '0' * 64}])
def test_incompatible_evaluators_cannot_be_locked(change):
    with pytest.raises(ContractViolation, match='incompatible evaluator'):
        resolve_lock([], fetch=lambda _id: None, ruleset=RULESET, registry=REGISTRY,
                     evaluator={**evaluator_artifact(), **change}, configuration={})


# --- evaluator identity --------------------------------------------------------------------------------

PINNED_EVALUATOR_DIGEST = "sha256:f2a1fe58c32bbbb82be482c7813d8c98ed348047e954f9564009bfa43a395e43"


def test_evaluator_descriptor_changes_require_a_version_bump():
    """If this fails, the evaluation profile changed: bump EVALUATOR_VERSION and re-pin the digest."""
    artifact = evaluator_artifact()
    assert (EVALUATOR_VERSION, artifact["digest"]) == ("1.0.0", PINNED_EVALUATOR_DIGEST)


def test_evaluator_digest_covers_code_even_when_the_descriptor_is_unchanged(tmp_path, monkeypatch):
    from vtt.creation_engine.evaluator import identity
    for name in identity._SOURCE_FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((identity._ROOT / name).read_bytes())
    original = evaluator_artifact()
    descriptor = identity.evaluator_descriptor()
    monkeypatch.setattr(identity, '_ROOT', tmp_path)
    assert evaluator_artifact() == original
    functions = tmp_path / 'evaluator/functions.py'
    functions.write_bytes(functions.read_bytes() + b'\n# changed implementation artifact\n')
    assert identity.evaluator_descriptor() == descriptor
    assert evaluator_artifact()['digest'] != original['digest']


def test_registry_snapshots_schemas_instead_of_following_mutable_input():
    import copy
    schema = copy.deepcopy(ITEM_SCHEMA)
    registry = SchemaRegistry('test.frozen', '1', [SchemaType(ITEM.type_id, ITEM.version, schema)])
    artifact = registry.artifact()
    schema['required'].clear()
    registry.get(ITEM).schema['required'].clear()
    assert registry.artifact() == artifact
    with pytest.raises(ContractViolation):
        registry.validate(ITEM, {})


def test_lock_resolution_verifies_actual_revision_bytes():
    from dataclasses import replace
    original = revision()
    forged = replace(original, canonical=b'{"name":"Different bytes"}')
    with pytest.raises(ContractViolation, match='digest'):
        _lock([forged], [original.ref()])


def test_lock_resolution_verifies_returned_revision_identity():
    original = revision()
    with pytest.raises(ContractViolation, match='identity'):
        resolve_lock([RevisionRef('rev:missing', original.definition_id, original.digest)], fetch=lambda _id: original,
                     ruleset=RULESET, registry=REGISTRY, evaluator=evaluator_artifact(), configuration={})
