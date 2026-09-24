"""WP1: wire-contract validation against core contract 1.1.3 and registry addendum A1 (spec v1.1.4 §17).

The examples come from the approved packages in docs/creation-engine/, so the
code is checked against the same evidence the spec review used.
"""

import copy
import json
from pathlib import Path

import pytest

from vtt.creation_engine.contracts import (CONTRACT_VERSION, REGISTRY_SCHEMA_ID, parse_command, validate_command,
                                           validate_definition)
from vtt.creation_engine.errors import SCHEMA_INVALID, ContractViolation

DOCS = Path(__file__).resolve().parents[2] / "docs" / "creation-engine"
CORE_EXAMPLE = json.loads((DOCS / "v1.1.3" / "creation-engine-v1.1.3-wire-examples.json").read_text())["valid_command"]
REGISTRY_EXAMPLES = json.loads((DOCS / "addenda" / "creation-engine-v1.1-registry-a1-verification.json").read_text())["examples"]
ZERO = "sha256:" + "0" * 64


def _rejected(envelope):
    with pytest.raises(ContractViolation) as caught:
        validate_command(envelope)
    assert caught.value.code == SCHEMA_INVALID
    return caught.value


def _variant(base, change):
    envelope = copy.deepcopy(base)
    change(envelope)
    return envelope


RESOLVE = {"contractVersion": CONTRACT_VERSION, "commandId": "cmd:2", "idempotencyKey": "idem:2", "scopeId": "campaign:demo",
           "expectedScopeVersion": 41, "authorityEpoch": 1, "executionLockDigest": ZERO, "operation": "ResolveDecision",
           "payload": {"actionId": "act:1", "decisionId": "dec:1", "expectedDecisionVersion": 1,
                       "contextToken": "ctx:" + "A" * 43, "answer": {"kind": "boolean", "value": True}}}


def test_core_examples_validate():
    validate_command(CORE_EXAMPLE)
    validate_command(RESOLVE)


@pytest.mark.parametrize("operation", sorted(REGISTRY_EXAMPLES))
def test_every_registry_operation_example_validates(operation):
    validate_command(REGISTRY_EXAMPLES[operation])


CORE_NEGATIVES = {
    "spoofed_principal_field": lambda c: c.__setitem__("principalId", "user:1"),
    "missing_epoch": lambda c: c.pop("authorityEpoch"),
    "unknown_operation": lambda c: c.__setitem__("operation", "DeleteEverything"),
    "malformed_hash": lambda c: c.__setitem__("executionLockDigest", "sha256:xyz"),
    "unknown_payload_field": lambda c: c["payload"].__setitem__("surprise", 1),
    "superseded_contract_version": lambda c: c.__setitem__("contractVersion", "1.1.2"),
    "bare_actor_id_G0_03": lambda c: (c["payload"].pop("actorInstance"), c["payload"].__setitem__("actorInstanceId", "actor:demo")),
    "missing_source_occurrence_G0_03": lambda c: c["payload"].pop("sourceInstance"),
}


@pytest.mark.parametrize("case", sorted(CORE_NEGATIVES))
def test_core_negative_cases_are_rejected(case):
    _rejected(_variant(CORE_EXAMPLE, CORE_NEGATIVES[case]))


def test_context_digest_fields_and_unkeyed_tokens_are_rejected():
    old_field = _variant(RESOLVE, lambda c: c["payload"].update({"contextDigest": ZERO}) or c["payload"].pop("contextToken"))
    unkeyed = _variant(RESOLVE, lambda c: c["payload"].update({"contextToken": ZERO}))
    _rejected(old_field)
    _rejected(unkeyed)


REGISTRY_NEGATIVES = {
    "unknown_payload_field": lambda c: c["payload"].__setitem__("surprise", 1),
    "spoofed_principal_field": lambda c: c.__setitem__("spoofedPrincipal", "user:1"),
    "missing_epoch": lambda c: c.pop("authorityEpoch"),
    "superseded_contract_version": lambda c: c.__setitem__("contractVersion", "1.1.2"),
}


@pytest.mark.parametrize("operation", sorted(REGISTRY_EXAMPLES))
@pytest.mark.parametrize("case", sorted(REGISTRY_NEGATIVES))
def test_registry_negative_cases_are_rejected(operation, case):
    _rejected(_variant(REGISTRY_EXAMPLES[operation], REGISTRY_NEGATIVES[case]))


def test_draft_operation_in_a_mechanical_envelope_is_rejected():
    mechanical = {k: v for k, v in REGISTRY_EXAMPLES["SetItemEquipped"].items() if k not in ("operation", "payload")}
    _rejected(dict(mechanical, operation="RecordDraftDecision", payload=REGISTRY_EXAMPLES["RecordDraftDecision"]["payload"]))


def test_rejection_names_the_offending_path():
    violation = _rejected(_variant(CORE_EXAMPLE, lambda c: c["payload"]["targets"][0].__setitem__("kind", "world")))
    assert violation.path[:2] == ("payload", "targets")


def test_parse_command_rejects_duplicate_keys_before_schema_validation():
    raw = json.dumps(CORE_EXAMPLE)[:-1] + ', "operation": "InvokeActivity"}'
    with pytest.raises(ContractViolation) as caught:
        parse_command(raw)
    assert "duplicate" in caught.value.detail


def test_parse_command_returns_the_validated_envelope():
    assert parse_command(json.dumps(CORE_EXAMPLE).encode("utf-8")) == CORE_EXAMPLE


PENDING = {"decisionId": "dec:1", "actionId": "act:1", "checkpointId": "cp:1", "questionId": "q:flame.spend", "questionVersion": 1,
           "answerSchemaDigest": ZERO, "contextToken": "ctx:" + "B" * 43, "decisionVersion": 1, "responderRuleId": "rule:controller",
           "targets": [], "createdAt": "2026-09-24T12:00:00Z", "deadline": "2026-09-24T12:02:00.5Z", "windowId": "window:after-hit",
           "timeoutPolicy": "decline_optional", "status": "open", "policyId": "policy:default"}
RECEIPT = {"commandId": "cmd:1", "operationId": "op:1", "requestDigest": ZERO, "status": "committed", "scopeId": "campaign:demo",
           "stateVersion": 41, "authorityEpoch": 1, "checkpointId": "cp:1", "errorCode": None, "eventIds": ["ev:1"]}


def test_definitions_validate_individually():
    validate_definition("PendingDecision", PENDING)
    validate_definition("PublicReceipt", RECEIPT)
    literal = {"node": "literal", "value": {"value": {"numerator": 12, "denominator": 1}, "unit": "unit:dimensionless"}}
    validate_definition("Predicate", {"node": "compare", "operator": "ge", "left": literal, "right": literal})
    validate_definition("CreateDraftPayload", {"schemaType": {"typeId": "rdl.equipment", "version": 1}, "authoringLocale": "fr"},
                        schema_id=REGISTRY_SCHEMA_ID)


@pytest.mark.parametrize("name, value", [
    ("PendingDecision", dict(PENDING, deadline="2026-09-24T14:02:00+02:00")),   # G0-20: UTC only
    ("PendingDecision", dict(PENDING, createdAt="2026-09-24T12:00:00")),
    ("PublicReceipt", dict(RECEIPT, outcomeDigest=ZERO)),                       # G0-01: no outcome digest
    ("Predicate", {"node": "and", "args": [{"node": "is_known", "bindingId": "x"}]}),
    ("Predicate", {"node": "xor", "args": []}),                                 # G0-10: unknown node
    ("Predicate", {"node": "binding"}),                                         # G0-10: missing binding
])
def test_invalid_definition_values_are_rejected(name, value):
    with pytest.raises(ContractViolation):
        validate_definition(name, value)


def test_unknown_definition_name_is_a_programming_error():
    with pytest.raises(KeyError):
        validate_definition("NoSuchDefinition", {})
