"""WP3 store: the content repository on SQLite (always) and on a disposable PostgreSQL 16 (marker ``postgres``).

The PostgreSQL run builds the content tables from migration m73 alone, so it
also proves the hand-applied SQL matches the models. It checks the
append-only triggers and two genuinely competing draft saves (spec §21:
competing transactions, not mocks that always serialize).
"""

import os
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import vtt.models  # noqa: F401  -- legacy tables the content tables reference (users, roles)
from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import DraftAnswer, ExecutionLock, resolve_lock
from vtt.creation_engine.errors import DRAFT_VERSION_CONFLICT, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.models import CONTENT_TABLES
from vtt.extensions import db

from test_ce_content import ITEM, NOW, REGISTRY, RULESET, revision

M73 = Path(__file__).resolve().parents[2] / "migrations" / "migration_m73_creation_engine_content.sql"
DISPOSABLE_DATABASE = "ce_test"          # tools/ce_test_postgres.py; the fixture refuses any other database


def _seed_account(connection) -> None:
    connection.execute(text("INSERT INTO roles (id, name) VALUES (1, 'player')"))
    connection.execute(text("INSERT INTO users (id, username, email, password_hash, role_id) "
                            "VALUES (1, 'author', 'author@example.test', 'x', 1)"))


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite://")
    db.metadata.create_all(engine)
    with engine.begin() as connection:
        _seed_account(connection)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def postgres_engine():
    url = os.environ.get("CE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("CE_TEST_DATABASE_URL is not set (python tools/ce_test_postgres.py start)")
    if urlparse(url).path.lstrip("/") != DISPOSABLE_DATABASE:
        pytest.skip(f"refusing to reset a database other than the disposable '{DISPOSABLE_DATABASE}'")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    db.metadata.create_all(engine, tables=[t for t in db.metadata.sorted_tables if not t.name.startswith("ce_")])
    with engine.begin() as connection:
        cursor = connection.connection.cursor()        # plain DBAPI, no parameters: '%' in PL/pgSQL stays literal
        cursor.execute(M73.read_text(encoding="utf-8"))  # content tables come from m73 only
        cursor.close()
        _seed_account(connection)
    yield engine
    engine.dispose()


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=pytest.mark.postgres)])
def engine(request):
    return request.getfixturevalue(f"{request.param}_engine")


def _definition(store, name="Flame sword"):
    workspace = store.workspace_for(1, now=NOW)
    return store.add_definition(workspace.id, name, ITEM.type_id, now=NOW)


def test_workspace_is_personal_and_created_once(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        assert store.workspace_for(1, now=NOW).id == store.workspace_for(1, now=NOW).id
        session.commit()


def test_revisions_round_trip_byte_identical(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        stored = revision(_definition(store).id, content={"name": "Flame sword", "bonus": {
            "value": {"numerator": 1, "denominator": 1}, "unit": "unit:point"}})
        store.append_revision(stored)
        session.commit()
    with Session(engine) as session:
        loaded = ContentStore(session).revision(stored.id)
    assert (loaded.canonical, loaded.digest, loaded.schema_type, loaded.provenance, loaded.definition_id) == \
        (stored.canonical, stored.digest, stored.schema_type, stored.provenance, stored.definition_id)


def test_revisions_need_a_live_definition_of_their_type(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        definition = _definition(store)
        store.tombstone_definition(definition.id, now=NOW)
        with pytest.raises(ContractViolation) as caught:
            store.append_revision(revision(definition.id))
        assert caught.value.code == SEMANTIC_INVALID
        other = store.add_definition(store.workspace_for(1, now=NOW).id, "Lore", "test.lore", now=NOW)
        with pytest.raises(ContractViolation, match="schema type"):
            store.append_revision(revision(other.id))


def test_definition_names_are_labels_and_deleted_ids_stay_reserved(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        definition = _definition(store)
        assert store.rename_definition(definition.id, "Flammenschwert").id == definition.id
        store.tombstone_definition(definition.id, now=NOW)
        assert store.definition(definition.id).tombstoned_at is not None
        with pytest.raises(ContractViolation):
            store.rename_definition(definition.id, "Again")


def test_draft_versions_conflicts_and_undo(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        workspace = store.workspace_for(1, now=NOW)
        draft = store.create_draft(workspace.id, ITEM, "de", {"name": "a"}, author_user_id=1, now=NOW, registry=REGISTRY)
        assert draft.version == 1
        assert store.advance_draft(draft.id, 1, {"name": "b"}, author_user_id=1, now=NOW).version == 2
        with pytest.raises(ContractViolation) as caught:
            store.advance_draft(draft.id, 1, {"name": "stale tab"}, author_user_id=1, now=NOW)
        assert caught.value.code == DRAFT_VERSION_CONFLICT
        reverted = store.revert_draft(draft.id, 2, 1, author_user_id=1, now=NOW)
        assert reverted.schema_bundle == draft.schema_bundle == canonical_bytes(REGISTRY.artifact())
        assert (reverted.version, parse_strict_json(reverted.content)) == (3, {"name": "a"})
        assert parse_strict_json(store.draft_version_content(draft.id, 2)) == {"name": "b"}     # history kept
        session.commit()


def test_decision_log_keeps_order(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        draft = store.create_draft(store.workspace_for(1, now=NOW).id, ITEM, "fr", {}, author_user_id=1, now=NOW, registry=REGISTRY)
        for version, question in ((2, "q:effect"), (3, "q:damage")):
            store.advance_draft(draft.id, version - 1, {}, author_user_id=1, now=NOW)
            store.append_answer(DraftAnswer(draft.id, version, question, 1, b'{"kind":"boolean","value":true}', "fr", 1,
                                            b"[]", b"[]", NOW))
        assert [a.question_id for a in store.answers(draft.id)] == ["q:effect", "q:damage"]
        session.commit()


def test_locks_are_content_addressed_and_immutable_in_the_store(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        stored = revision(_definition(store).id)
        store.append_revision(stored)
        lock = resolve_lock([stored.ref()], fetch=store.revision, ruleset=RULESET, registry=REGISTRY,
                            evaluator=evaluator_artifact(), configuration={"campaign": "store-test"})
        store.save_lock(lock, now=NOW)
        store.save_lock(lock, now=NOW)                       # same content: idempotent
        assert store.lock(lock.lock_id) == lock
        with pytest.raises(ContractViolation, match="different content"):
            store.save_lock(ExecutionLock(lock.lock_id, lock.canonical, "sha256:" + "0" * 64), now=NOW)
        session.commit()


# --- PostgreSQL only ------------------------------------------------------------------------------

@pytest.mark.postgres
def test_m73_matches_the_models(postgres_engine):
    inspector = inspect(postgres_engine)
    for table in CONTENT_TABLES:
        actual = {c["name"]: (c["nullable"], c["type"].compile(dialect=postgres_engine.dialect))
                  for c in inspector.get_columns(table.name)}
        assert actual == {c.name: (c.nullable, c.type.compile(dialect=postgres_engine.dialect))
                          for c in table.columns}, table.name
        assert inspector.get_pk_constraint(table.name)['constrained_columns'] == [c.name for c in table.primary_key]
        expected_fks = {(tuple(c.parent.name for c in constraint.elements),
                         tuple(c.target_fullname for c in constraint.elements)) for constraint in table.foreign_key_constraints}
        actual_fks = {(tuple(fk['constrained_columns']),
                       tuple(f"{fk['referred_table']}.{column}" for column in fk['referred_columns']))
                      for fk in inspector.get_foreign_keys(table.name)}
        assert actual_fks == expected_fks, table.name


@pytest.mark.postgres
def test_m73_can_be_reapplied_without_losing_content(postgres_engine):
    with Session(postgres_engine) as session:
        store = ContentStore(session)
        store.append_revision(revision(_definition(store).id))
        session.commit()
    with postgres_engine.begin() as connection:
        before = connection.execute(text('SELECT COUNT(*) FROM ce_revisions')).scalar_one()
        assert before > 0
        with connection.connection.cursor() as cursor:
            cursor.execute(M73.read_text(encoding='utf-8'))
        assert connection.execute(text('SELECT COUNT(*) FROM ce_revisions')).scalar_one() == before


@pytest.mark.postgres
@pytest.mark.parametrize("statement", [
    "UPDATE ce_revisions SET digest = 'sha256:x'",
    "DELETE FROM ce_revisions",
    "UPDATE ce_draft_versions SET content = 'x'",
    "DELETE FROM ce_draft_versions",
    "UPDATE ce_draft_answers SET question_version = 2",
    "DELETE FROM ce_draft_answers",
    "UPDATE ce_execution_locks SET digest = 'sha256:x'",
    "DELETE FROM ce_execution_locks",
])
def test_append_only_records_reject_update_and_delete(postgres_engine, statement):
    with Session(postgres_engine) as session:
        store = ContentStore(session)
        stored = revision(_definition(store).id)
        store.append_revision(stored)
        draft = store.create_draft(store.workspace_for(1, now=NOW).id, ITEM, "de", {}, author_user_id=1, now=NOW, registry=REGISTRY)
        store.append_answer(DraftAnswer(draft.id, 1, "q:x", 1, b'{"kind":"boolean","value":true}', "de", 1, b"[]", b"[]", NOW))
        store.save_lock(resolve_lock([stored.ref()], fetch=store.revision, ruleset=RULESET, registry=REGISTRY,
                                     evaluator=evaluator_artifact(), configuration={"trigger": statement}), now=NOW)
        session.commit()
    with postgres_engine.connect() as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(text(statement))


@pytest.mark.postgres
def test_two_tabs_saving_the_same_draft_version_cannot_both_win(postgres_engine):
    with Session(postgres_engine) as session:
        store = ContentStore(session)
        draft = store.create_draft(store.workspace_for(1, now=NOW).id, ITEM, "de", {"name": "v1"}, author_user_id=1, now=NOW, registry=REGISTRY)
        session.commit()
    start, outcomes = threading.Barrier(2), []

    def save(tab):
        with Session(postgres_engine) as session:
            start.wait()
            try:
                ContentStore(session).advance_draft(draft.id, 1, {"name": tab}, author_user_id=1, now=NOW)
                time.sleep(0.3)                    # hold the row lock so the other save must wait for this commit
                session.commit()
                outcomes.append("saved")
            except ContractViolation as violation:
                session.rollback()
                outcomes.append(violation.code)

    tabs = [threading.Thread(target=save, args=(name,)) for name in ("tab-a", "tab-b")]
    for tab in tabs:
        tab.start()
    for tab in tabs:
        tab.join()
    assert sorted(outcomes) == [DRAFT_VERSION_CONFLICT, "saved"]
    with Session(postgres_engine) as session:
        assert ContentStore(session).draft(draft.id).version == 2


@pytest.mark.parametrize('operation', ['create', 'advance'])
def test_invalid_draft_json_cannot_leave_a_partial_head(engine, operation):
    """Catching a rejected edit and committing other work must not corrupt history."""
    with Session(engine) as session:
        store = ContentStore(session)
        workspace = store.workspace_for(1, now=NOW)
        draft = store.create_draft(workspace.id, ITEM, 'de', {'name': 'original'}, author_user_id=1, now=NOW, registry=REGISTRY)
        session.commit()
        before = session.execute(text('SELECT COUNT(*) FROM ce_drafts')).scalar_one()
        with pytest.raises(ContractViolation):
            if operation == 'create':
                store.create_draft(workspace.id, ITEM, 'de', {'bad': float('nan')}, author_user_id=1, now=NOW, registry=REGISTRY)
            else:
                store.advance_draft(draft.id, 1, {'bad': float('nan')}, author_user_id=1, now=NOW)
        session.commit()
        assert session.execute(text('SELECT COUNT(*) FROM ce_drafts')).scalar_one() == before
        loaded = store.draft(draft.id)
        assert loaded.version == 1
        assert parse_strict_json(loaded.content) == {'name': 'original'}


def test_revision_store_rejects_bytes_that_disagree_with_digest(engine):
    from dataclasses import replace
    with Session(engine) as session:
        store = ContentStore(session)
        stored = revision(_definition(store).id)
        with pytest.raises(ContractViolation, match='digest'):
            store.append_revision(replace(stored, canonical=b'{"name":"Forged"}'))
        session.commit()
        assert store.revision(stored.id) is None


def test_lock_store_rejects_forged_canonical_bytes(engine):
    from dataclasses import replace
    with Session(engine) as session:
        store = ContentStore(session)
        stored = revision(_definition(store).id)
        lock = resolve_lock([stored.ref()], fetch={stored.id: stored}.get, ruleset=RULESET, registry=REGISTRY,
                            evaluator=evaluator_artifact(), configuration={})
        with pytest.raises(ContractViolation):
            store.save_lock(replace(lock, canonical=b'{}'), now=NOW)
        session.commit()
        assert store.lock(lock.lock_id) is None


@pytest.mark.parametrize('version', [0, 2**53 - 1])
def test_store_preserves_the_contracts_full_schema_version_range(engine, version):
    from vtt.creation_engine.content import SchemaRegistry, SchemaType, SchemaTypeRef, create_revision
    registry = SchemaRegistry('test.version-range', '1', [SchemaType('test.item', version, {'type': 'object'})])
    schema_type = SchemaTypeRef('test.item', version)
    with Session(engine) as session:
        store = ContentStore(session)
        definition = _definition(store)
        stored = create_revision(definition.id, schema_type, {}, registry=registry, author_user_id=1,
                                 provenance={}, now=NOW)
        store.append_revision(stored)
        draft = store.create_draft(definition.workspace_id, schema_type, 'en', {}, registry=registry,
                                   author_user_id=1, now=NOW)
        session.commit()
        assert store.revision(stored.id).schema_type == store.draft(draft.id).schema_type == schema_type


def test_decision_log_cannot_reference_a_missing_snapshot(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        draft = store.create_draft(store.workspace_for(1, now=NOW).id, ITEM, 'de', {}, registry=REGISTRY,
                                   author_user_id=1, now=NOW)
        with pytest.raises(ContractViolation, match='has no version'):
            store.append_answer(DraftAnswer(draft.id, 2, 'q:x', 1, b'{"kind":"boolean","value":true}',
                                            'de', 1, b'[]', b'[]', NOW))
        session.commit()
        assert store.answers(draft.id) == ()


def test_draft_cannot_attach_to_a_definition_of_another_type(engine):
    with Session(engine) as session:
        store = ContentStore(session)
        workspace = store.workspace_for(1, now=NOW)
        definition = store.add_definition(workspace.id, 'Lore', 'test.lore', now=NOW)
        with pytest.raises(ContractViolation, match='workspace and schema type'):
            store.create_draft(workspace.id, ITEM, 'de', {}, registry=REGISTRY, definition_id=definition.id,
                               author_user_id=1, now=NOW)


@pytest.mark.postgres
@pytest.mark.parametrize('operation', ['workspace', 'lock'])
def test_simultaneous_first_insert_is_idempotent(postgres_engine, operation):
    """Two transactions really race on the unique key; both may commit."""
    with postgres_engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, username, email, password_hash, role_id) "
                                "VALUES (100, 'concurrent', 'concurrent@example.test', 'x', 1) "
                                "ON CONFLICT (id) DO NOTHING"))
    lock = resolve_lock([], fetch=lambda _id: None, ruleset=RULESET, registry=REGISTRY,
                        evaluator=evaluator_artifact(), configuration={'concurrent': operation})
    barrier = threading.Barrier(2)
    def insert():
        with Session(postgres_engine) as session:
            barrier.wait(timeout=10)
            store = ContentStore(session)
            if operation == 'workspace':
                result = store.workspace_for(100, now=NOW).id
            else:
                store.save_lock(lock, now=NOW)
                result = store.lock(lock.lock_id).lock_id
            time.sleep(0.1)
            session.commit()
            return result
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(insert) for _ in range(2)]
        outcomes = [future.result(timeout=15) for future in futures]
    assert outcomes[0] == outcomes[1]
