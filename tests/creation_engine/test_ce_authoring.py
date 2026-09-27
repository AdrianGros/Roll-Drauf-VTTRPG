"""WP8 private drafts on PostgreSQL: retries, races, rollback and immutable history."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.compiler import flame
from vtt.creation_engine.content import new_id
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.authoring import QualityClaimUnmet
from vtt.creation_engine.store.authoring_models import AUTHORING_TABLES, CeAuthoringSnapshot, CeDraftCommand
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.models import CeDraft, CeDraftAnswer, CeDraftVersion, CeRevision
from vtt.creation_engine.transports.legacy_host import build_gateway
from vtt.models.user import User

from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine

pytestmark = pytest.mark.postgres
M78 = Path(__file__).resolve().parents[2] / "migrations/migration_m78_creation_engine_authoring.sql"


@pytest.fixture(scope="module")
def authoring_engine(migration_engine):
    with migration_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M78.read_text())
    return migration_engine


@pytest.fixture
def author(authoring_engine):
    gateway = build_gateway(authoring_engine)
    with Session(authoring_engine) as session, session.begin():
        user = User(username=new_id("author"), email=new_id("mail") + "@example.test", password_hash="x", role_id=1,
                    is_active=True, is_suspended=False, account_state="active")
        session.add(user); session.flush()
        principal = user.id
    service = gateway.authoring
    workspace = service.workspace(principal)
    context = {"gateway": gateway, "service": service, "principal": principal, "workspace": workspace["workspaceId"]}
    cmd = wire(context, "CreateDraft", {"schemaType": flame.ITEM_TYPE.to_wire(), "authoringLocale": "de"})
    gateway.submit(principal, canonical_bytes(cmd))
    result = service.command_result(principal, context["workspace"], cmd["idempotencyKey"])
    context["draft"] = result["draftId"]
    return context


def read(a, **kwargs):
    return a["service"].read(a["principal"], a["workspace"], a["draft"], **kwargs)


def wire(a, operation, payload, **changes):
    value = {"contractVersion": "1.1.3", "commandId": new_id("cmd"), "idempotencyKey": new_id("key"),
        "workspaceId": a["workspace"], "authorityEpoch": 1, "operation": operation, "payload": payload}
    if operation != "CreateDraft":
        value.update(draftId=a["draft"], expectedDraftVersion=read(a)["draftVersion"])
    return {**value, **changes}


def submit(a, operation, payload, **changes):
    command = wire(a, operation, payload, **changes)
    receipt = a["gateway"].submit(a["principal"], canonical_bytes(command))
    validate_definition("PublicReceipt", receipt)
    result = a["service"].command_result(a["principal"], a["workspace"], command["idempotencyKey"],
                                         draft_id=a.get("draft") if operation != "CreateDraft" else None)
    return receipt, result


def decision(key, value, locale="de"):
    question = flame.interview().by_id[key]
    return {"question": {"questionId": key, "questionVersion": question.version},
            "answer": question.answer(value), "promptLocale": locale}


def preset(a, name="g1.post-hit-flames"):
    preview = a["service"].preview(a["principal"], a["workspace"], name)
    return submit(a, "ApplyDraftPreset", {"preset": {"presetId": name, "version": 1},
                                         "previewDigest": preview["previewDigest"]})


def test_m78_matches_models_and_is_repeatable(authoring_engine):
    with authoring_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M78.read_text())
    inspector = inspect(authoring_engine)
    for table in AUTHORING_TABLES:
        assert {c["name"] for c in inspector.get_columns(table.name)} == set(table.columns.keys())
    assert next(c for c in inspector.get_columns("ce_workspace_commands") if c["name"] == "scope_id")["nullable"]


def test_saved_decisions_invalidate_effects_and_keep_history(author):
    preset(author)
    before = read(author)
    assert before["content"]["flames"]["damage"] == {"count": 2, "sides": 6}
    _, result = submit(author, "RecordDraftDecision", decision("flame.behavior", "visual", "fr"))
    view = read(author, mode="advanced", locale="en")
    assert "damage" not in view["content"]["flames"]
    assert "flame.damage" in result["invalidated"] and "flame.damage" in view["stale"]
    with Session(author["gateway"].store.engine) as session:
        answers = ContentStore(session).answers(author["draft"])
        assert any(a.question_id == "flame.damage" for a in answers)
        assert answers[-1].prompt_locale == "fr"
    history = author["service"].history(author["principal"], author["workspace"], author["draft"])
    assert len(history) == 2 and history[-1]["invalidated"] == result["invalidated"]


def test_retry_after_commit_and_lost_response_is_exactly_once(author):
    cmd = wire(author, "RecordDraftDecision", decision("item.name", "Retry sword"))
    def crash(point):
        if point == "after_commit":
            raise RuntimeError("lost response")
    author["gateway"].kernel.fault = crash
    with pytest.raises(RuntimeError):
        author["gateway"].submit(author["principal"], canonical_bytes(cmd))
    author["gateway"].kernel.fault = lambda p: None
    first = author["gateway"].submit(author["principal"], canonical_bytes(cmd))
    retry = author["gateway"].submit(author["principal"], canonical_bytes({**cmd, "commandId": new_id("cmd")}))
    assert retry == first and read(author)["draftVersion"] == 2
    changed = {**cmd, "payload": decision("item.name", "Changed")}
    with pytest.raises(ContractViolation, match="IDEMPOTENCY_KEY_REUSE"):
        author["gateway"].submit(author["principal"], canonical_bytes(changed))


def test_precommit_failure_rolls_back_content_answers_and_receipt(author):
    cmd = wire(author, "RecordDraftDecision", decision("item.name", "Never committed"))
    def crash(point):
        if point == "before_commit":
            raise RuntimeError("database transaction failed")
    author["gateway"].kernel.fault = crash
    with pytest.raises(RuntimeError):
        author["gateway"].submit(author["principal"], canonical_bytes(cmd))
    author["gateway"].kernel.fault = lambda p: None
    assert read(author)["content"] == {} and read(author)["draftVersion"] == 1
    with Session(author["gateway"].store.engine) as session:
        for model in (CeDraftAnswer, CeDraftCommand):
            assert not session.scalar(select(func.count()).select_from(model).where(model.draft_id == author["draft"]))
        assert session.scalar(select(func.count()).select_from(CeAuthoringSnapshot).where(CeAuthoringSnapshot.draft_id == author["draft"])) == 1


def test_two_competing_saves_cannot_overwrite_each_other(author):
    commands = [wire(author, "RecordDraftDecision", decision("item.name", name)) for name in ("First", "Second")]
    barrier = Barrier(2)
    def save(command):
        barrier.wait(timeout=10)
        try:
            return author["gateway"].submit(author["principal"], canonical_bytes(command))["status"]
        except ContractViolation as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, commands))
    assert sorted(results) == ["DRAFT_VERSION_CONFLICT", "committed"]
    assert read(author)["draftVersion"] == 2


def test_current_authority_is_checked_before_retry_or_private_reads(author):
    cmd = wire(author, "RecordDraftDecision", decision("item.name", "Private"))
    author["gateway"].submit(author["principal"], canonical_bytes(cmd))
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        author["service"].read(1, author["workspace"], author["draft"])
    with Session(author["gateway"].store.engine) as session, session.begin():
        session.get(User, author["principal"]).is_suspended = True
    for operation in (lambda: read(author), lambda: author["gateway"].submit(author["principal"], canonical_bytes(cmd))):
        with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
            operation()


def test_revert_restores_answers_as_new_version(author):
    preset(author)
    original = read(author)
    submit(author, "RecordDraftDecision", decision("flame.behavior", "visual"))
    submit(author, "RevertDraft", {"toDraftVersion": original["draftVersion"]})
    restored = read(author)
    assert restored["content"] == original["content"] and restored["stale"] == {}
    assert restored["draftVersion"] == original["draftVersion"] + 2
    assert len(author["service"].history(author["principal"], author["workspace"], author["draft"])) == 3


def test_quality_claims_are_verified_and_revision_provenance_is_pinned(author):
    submit(author, "RecordDraftDecision", decision("item.name", "Harmless prose"))
    with pytest.raises(QualityClaimUnmet) as error:
        submit(author, "CommitDraftRevision", {"declaredQuality": "runtime_ready", "definition": {"kind": "new"}})
    assert error.value.gates and read(author)["draftVersion"] == 2
    preset(author, "g1.harmless-flames")
    _, result = submit(author, "CommitDraftRevision", {"declaredQuality": "sheet_ready", "definition": {"kind": "new"}})
    with Session(author["gateway"].store.engine) as session:
        revision = ContentStore(session).revision(result["revision"]["id"])
        provenance = parse_strict_json(revision.provenance)
        assert provenance["registry"] == author["service"].registry.artifact()
        assert provenance["compilerVersion"] == flame.COMPILER_VERSION
        assert revision.content["flames"]["behavior"] == "visual" and "damage" not in revision.content["flames"]
        assert session.get(CeDraft, author["draft"]).definition_id == result["revision"]["definitionId"]
    with pytest.raises(QualityClaimUnmet):
        submit(author, "CommitDraftRevision", {"declaredQuality": "automation_complete", "definition": {"kind": "new"}})


@pytest.mark.parametrize("mode", ["guided", "structured", "advanced"])
@pytest.mark.parametrize("locale", ["de", "en", "fr"])
def test_locale_and_mode_reads_are_not_mutations(author, mode, locale):
    preset(author)
    before = read(author)
    after = read(author, mode=mode, locale=locale)
    assert before["content"] == after["content"] and before["draftVersion"] == after["draftVersion"]
    assert after["locale"] == locale and after["mode"] == mode


def test_registry_change_requires_reviewed_migration(author):
    from vtt.creation_engine.content import SchemaRegistry, SchemaType
    author["service"].registry = SchemaRegistry("g1.authoring-schemas", "2", [SchemaType("fixture", 1, {"type": "object"})])
    with pytest.raises(ContractViolation, match="AUTHORING_REGISTRY_MISMATCH"):
        read(author)


def test_workspace_creation_retries_and_migration_share_key_namespace(author):
    from vtt.creation_engine.store.runtime_models import CeRuntimeScope
    from vtt.models.campaign import Campaign
    command = wire(author, "CreateDraft", {"schemaType": flame.ITEM_TYPE.to_wire(), "authoringLocale": "fr"})
    first = author["gateway"].submit(author["principal"], canonical_bytes(command))
    retry = author["gateway"].submit(author["principal"], canonical_bytes(command))
    assert retry == first
    result = author["service"].command_result(author["principal"], author["workspace"], command["idempotencyKey"])
    assert author["service"].read(author["principal"], author["workspace"], result["draftId"])["authoringLocale"] == "fr"
    with Session(author["gateway"].store.engine) as session, session.begin():
        campaign = Campaign(name="Key collision fixture", owner_id=author["principal"])
        session.add(campaign); session.flush()
        campaign_id = campaign.id
        count = session.scalar(select(func.count()).select_from(CeRuntimeScope))
    collision = {**command, "operation": "OpenLegacyCampaignScope", "payload": {"legacyCampaignId": campaign_id}}
    with pytest.raises(ContractViolation, match="IDEMPOTENCY_KEY_REUSE"):
        author["gateway"].submit(author["principal"], canonical_bytes(collision))
    with Session(author["gateway"].store.engine) as session:
        assert session.scalar(select(func.count()).select_from(CeRuntimeScope)) == count


def test_rejected_preset_and_required_skip_leave_no_version_or_log(author):
    for operation, payload, code in [
        ("ApplyDraftPreset", {"preset": {"presetId": "g1.harmless-flames", "version": 1}, "previewDigest": "sha256:" + "0" * 64}, "PRESET_PREVIEW_STALE"),
        ("SkipDraftQuestion", {"question": {"questionId": "item.name", "questionVersion": 1}}, "QUESTION_REQUIRED"),
    ]:
        with pytest.raises(ContractViolation, match=code):
            submit(author, operation, payload)
    assert read(author)["draftVersion"] == 1
    assert author["service"].history(author["principal"], author["workspace"], author["draft"]) == []


def test_committed_revision_is_unchanged_by_future_decisions(author):
    preset(author, "g1.harmless-flames")
    _, result = submit(author, "CommitDraftRevision", {"declaredQuality": "sheet_ready", "definition": {"kind": "new"}})
    submit(author, "RecordDraftDecision", decision("item.name", "A later decision"))
    with Session(author["gateway"].store.engine) as session:
        revision = ContentStore(session).revision(result["revision"]["id"])
        assert revision.content["name"] == "Flame sword"
        assert read(author)["content"]["name"] == "A later decision"


def test_preset_records_the_language_actually_shown_in_its_sealed_preview(author):
    preview = author['service'].preview(author['principal'], author['workspace'], 'g1.harmless-flames', locale='fr')
    submit(author, 'ApplyDraftPreset', {'preset': {'presetId': 'g1.harmless-flames', 'version': 1}, 'previewDigest': preview['previewDigest']})
    with Session(author['gateway'].store.engine) as session:
        answers = ContentStore(session).answers(author['draft'])
        assert answers and {answer.prompt_locale for answer in answers} == {'fr'}
    assert read(author)['authoringLocale'] == 'de'


@pytest.mark.parametrize("table", ["ce_authoring_snapshots", "ce_draft_commands", "ce_workspace_results"])
def test_authoring_evidence_is_database_immutable(author, table):
    submit(author, "RecordDraftDecision", decision("item.name", "Immutable"))
    with pytest.raises(DBAPIError):
        with author["gateway"].store.engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {table}"))
