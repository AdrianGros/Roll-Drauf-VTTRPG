"""WP6 pure information-flow boundaries and the F-CURSE fixture."""

from dataclasses import replace

import pytest

from vtt.creation_engine.canonical import canonical_bytes, content_digest
from vtt.creation_engine.policy import (Grant, Policy, PolicySet, Principal, Declassification,
                                        Document, Field, Source, project, public_receipt, cache_key)

PLAYER = Principal(2, frozenset({"member"}))
GM = Principal(1, frozenset({"member", "operator"}))
READS = ("read", "explain", "export")
OPEN = tuple(Grant(op, roles=("member",)) for op in READS) + (Grant("compute", roles=("engine",)),)
RULE = Declassification("disclosure:curse-final", frozenset({"defense"}), frozenset({"base", "curse"}),
                        tuple(Grant(op, roles=("member",)) for op in READS))


def policies():
    return PolicySet("scope:test", [Policy("scope:test", None, OPEN),
        Policy("policy:sheet", "scope:test", OPEN),
        Policy("policy:curse", "scope:test", OPEN, owner_id=1, owner_grants=(Grant("compute", roles=("engine",)),)),
        Policy("policy:owner", "scope:test", OPEN, owner_id=2)])


def curse():
    return Document("sheet:hero", "policy:sheet", {
        "name": Field("Hero", "policy:sheet"),
        "defense": Field(12, "policy:sheet", (Source("policy:sheet", "base"), Source("policy:curse", "curse")), RULE.id),
        "sourceName": Field("Secret curse", "policy:curse"),
        "sourceId": Field("effect:secret", "policy:curse"),
        "sourceURL": Field("https://private.invalid/curse", "policy:curse"),
        "privateNote": Field("Owner only", "policy:owner"),
        "proof": Field({"contributions": [{"name": "Secret curse", "value": -1}]}, "policy:sheet",
                       (Source("policy:curse", "curse"),)),
        "digest": Field(content_digest({"curse": -1}), "policy:sheet", (Source("policy:curse", "curse"),), RULE.id, True),
    })


@pytest.mark.parametrize("operation", READS)
@pytest.mark.parametrize("reviewed", [False, True])
def test_t22_hidden_curse_only_discloses_reviewed_final_value(operation, reviewed):
    result = project(curse(), policies(), (PLAYER,), operation=operation, declassifications=(RULE,) if reviewed else ())
    assert ("defense" in result["fields"]) == reviewed
    if reviewed:
        assert result["fields"]["defense"] == 12
    raw = canonical_bytes(result)
    for secret in (b"Secret curse", b"effect:secret", b"private.invalid", b"contributions", b"sha256:", b"omitted"):
        assert secret not in raw


def test_container_denial_cannot_be_widened_by_a_child_or_reveal():
    p = policies()
    root = p.policies["scope:test"]
    p.policies[root.id] = replace(root, denies=(Grant("read", principals=(2,)),))
    assert project(curse(), p, (PLAYER,), declassifications=(RULE,)) is None


def test_missing_grant_missing_parent_and_cycles_fail_closed():
    p = policies()
    assert not p.allows(PLAYER, "unknown")
    assert not p.allows(PLAYER, "policy:sheet", "adjust")
    p.policies["scope:test"] = replace(p.policies["scope:test"], parent_id="policy:sheet")
    assert not p.allows(PLAYER, "policy:sheet")


def test_t24_view_as_intersects_both_audiences_and_owner_private_rights():
    gm = project(curse(), policies(), (GM,), declassifications=(RULE,))
    assert gm["fields"]["sourceName"] == "Secret curse"
    assert "privateNote" not in gm["fields"]
    player = project(curse(), policies(), (PLAYER,), declassifications=(RULE,))
    assert player["fields"]["privateNote"] == "Owner only"
    viewed = project(curse(), policies(), (GM, PLAYER), declassifications=(RULE,))
    assert "sourceName" not in viewed["fields"] and "privateNote" not in viewed["fields"]


@pytest.mark.parametrize("change", ["field", "category", "audience", "compute", "digest"])
def test_declassification_cannot_expand_reviewed_boundary(change):
    rule, p = RULE, policies()
    if change == "field":
        rule = replace(rule, output_fields=frozenset({"other"}))
    elif change == "category":
        rule = replace(rule, input_categories=frozenset({"base"}))
    elif change == "audience":
        rule = replace(rule, audience=(Grant("read", roles=("operator",)),))
    elif change == "compute":
        private = p.policies["policy:curse"]
        p.policies[private.id] = replace(private, owner_grants=())
    else:
        rule = replace(rule, output_fields=frozenset({"digest"}))
    result = project(curse(), p, (PLAYER,), declassifications=(rule,))
    assert "defense" not in result["fields"] and "digest" not in result["fields"]


def test_no_unlabelled_dictionary_can_be_projected():
    with pytest.raises(TypeError):
        project({"secret": "value"}, policies(), (PLAYER,))
    with pytest.raises(TypeError):
        project(Document("x", "policy:sheet", {"name": "raw"}), policies(), (PLAYER,))


def test_hidden_children_do_not_leave_placeholders_or_counts():
    document = replace(curse(), children=(Document("secret:child", "policy:curse", {}),))
    assert project(document, policies(), (PLAYER,)) == project(curse(), policies(), (PLAYER,))


def test_t47_receipt_is_exact_allowlist_with_current_event_visibility():
    digest = "sha256:" + "0" * 64
    internal = {"commandId": "cmd:1", "operationId": "op:1", "requestDigest": digest,
        "status": "committed", "scopeId": "scope:test", "stateVersion": 1, "authorityEpoch": 1,
        "checkpointId": "checkpoint:private", "outcomeDigest": content_digest({"hiddenHP": 37}),
        "errorCode": None, "eventIds": ["event:private", "event:public"], "privateDiagnostic": "hidden"}
    result = public_receipt(internal, visible_event_ids=["event:public"])
    assert result["eventIds"] == ["event:public"] and result["checkpointId"] is None
    assert "outcomeDigest" not in result and "privateDiagnostic" not in result
    assert len(result) == 10


@pytest.mark.parametrize("field,value", [("scope_id", "scope:other"), ("policy_epoch", 2),
    ("state_version", 2), ("lock_digest", "sha256:" + "1" * 64), ("representation_version", "g1:2"),
    ("object_id", "other"), ("operation", "export"), ("access_stamp", "changed"), ("audience", (GM,)),
    ("audience", (replace(PLAYER, entitlement_epoch=1),)), ("audience", (GM, PLAYER))])
def test_t23_cache_identity_separates_every_authority_dimension(field, value):
    args = dict(audience=(PLAYER,), scope_id="scope:test", policy_epoch=1, access_stamp="current",
                state_version=1, lock_digest="sha256:" + "0" * 64, representation_version="g1:1", object_id="sheet", operation="read")
    assert cache_key(**args) != cache_key(**{**args, field: value})


def test_projected_values_are_independent_and_manual_outputs_are_labelled():
    doc = Document("manual:1", "policy:sheet", {"details": Field({"result": [12]}, "policy:sheet")}, manual=True)
    result = project(doc, policies(), (PLAYER,))
    result["fields"]["details"]["result"].append(42)
    again = project(doc, policies(), (PLAYER,))
    assert again["fields"]["details"]["result"] == [12]
    assert again["manual"] is True and again["automatedCompletion"] is False
