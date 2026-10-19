"""Content repository: the persistence adapter for WP3 records.

The caller owns the transaction; nothing here commits. Append-only records
have no update method at all. Advancing a draft is one conditional UPDATE on
the expected version, so two concurrent saves from the same version cannot
both win (the loser gets DRAFT_VERSION_CONFLICT).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.contracts import REGISTRY_SCHEMA_ID, validate_definition
from vtt.creation_engine.content import (Definition, Draft, DraftAnswer, ExecutionLock, Revision, SchemaRegistry, SchemaTypeRef,
                                         Workspace, new_id, require_draft_version)
from vtt.creation_engine.errors import DRAFT_VERSION_CONFLICT, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.store.models import (CeDefinition, CeDraft, CeDraftAnswer, CeDraftVersion, CeExecutionLock,
                                              CeRevision, CeWorkspace)


class ContentStore:
    def __init__(self, session):
        self.session = session

    # --- workspaces and definitions ------------------------------------------------------------

    def workspace_for(self, user_id: int, *, now: datetime) -> Workspace:
        """The account's personal workspace, created on first use (G1 plan §7)."""
        row = self.session.scalar(select(CeWorkspace).where(CeWorkspace.owner_user_id == user_id))
        if row is None:
            self._insert_once(CeWorkspace, {"id": new_id("ws"), "owner_user_id": user_id, "created_at": now},
                              conflict_columns=["owner_user_id"])
            row = self.session.scalar(select(CeWorkspace).where(CeWorkspace.owner_user_id == user_id))
        return Workspace(row.id, row.owner_user_id, row.created_at)

    def add_definition(self, workspace_id: str, name: str, schema_type_id: str, *, now: datetime) -> Definition:
        row = CeDefinition(id=new_id("def"), workspace_id=workspace_id, name=name, schema_type_id=schema_type_id,
                           created_at=now)
        self.session.add(row)
        self.session.flush()
        return _definition(row)

    def definition(self, definition_id: str) -> Definition | None:
        row = self.session.get(CeDefinition, definition_id)
        return _definition(row) if row else None

    def rename_definition(self, definition_id: str, name: str) -> Definition:
        row = self._live_definition(definition_id)
        row.name = name
        return _definition(row)

    def tombstone_definition(self, definition_id: str, *, now: datetime) -> Definition:
        """Soft deletion: the ID stays reserved and its revisions stay retained (§4)."""
        row = self._live_definition(definition_id)
        row.tombstoned_at = now
        return _definition(row)

    def _live_definition(self, definition_id: str) -> CeDefinition:
        row = self.session.get(CeDefinition, definition_id, populate_existing=True, with_for_update=True)
        if row is None or row.tombstoned_at is not None:
            raise ContractViolation(SEMANTIC_INVALID, f"definition {definition_id} does not exist or is deleted")
        return row

    # --- revisions (append-only) ----------------------------------------------------------------

    def append_revision(self, revision: Revision) -> None:
        revision.validate_integrity()
        definition = self._live_definition(revision.definition_id)
        if definition.schema_type_id != revision.schema_type.type_id:
            raise ContractViolation(SEMANTIC_INVALID, "revision schema type differs from its definition's type")
        self.session.add(CeRevision(
            id=revision.id, definition_id=revision.definition_id, schema_type_id=revision.schema_type.type_id,
            schema_version=revision.schema_type.version, canonical=revision.canonical, digest=revision.digest,
            provenance=revision.provenance, author_user_id=revision.author_user_id, created_at=revision.created_at))
        self.session.flush()

    def revision(self, revision_id: str) -> Revision | None:
        row = self.session.get(CeRevision, revision_id)
        if row is None:
            return None
        revision = Revision(row.id, row.definition_id, SchemaTypeRef(row.schema_type_id, row.schema_version), row.canonical,
                            row.digest, row.provenance, row.author_user_id, row.created_at)
        revision.validate_integrity()
        return revision

    # --- drafts ------------------------------------------------------------------------------------

    def create_draft(self, workspace_id: str, schema_type: SchemaTypeRef, authoring_locale: str, content: object, *,
                     author_user_id: int, now: datetime, registry: SchemaRegistry,
                     definition_id: str | None = None) -> Draft:
        # Reject invalid content before writing the draft head.
        canonical = canonical_bytes(content)
        registry.get(schema_type)
        if authoring_locale not in ("de", "en", "fr"):
            raise ContractViolation(SEMANTIC_INVALID, "unsupported authoring locale")
        if definition_id is not None:
            definition = self._live_definition(definition_id)
            if definition.workspace_id != workspace_id or definition.schema_type_id != schema_type.type_id:
                raise ContractViolation(SEMANTIC_INVALID, "draft definition must belong to its workspace and schema type")
        draft_id = new_id("draft")
        self.session.add(CeDraft(id=draft_id, workspace_id=workspace_id, definition_id=definition_id,
                                 schema_type_id=schema_type.type_id, schema_version=schema_type.version,
                                 authoring_locale=authoring_locale, schema_bundle=canonical_bytes(registry.artifact()),
                                 version=1, created_at=now, updated_at=now))
        self.session.flush()
        self.session.add(CeDraftVersion(draft_id=draft_id, version=1, content=canonical,
                                        author_user_id=author_user_id, created_at=now))
        self.session.flush()
        return self.draft(draft_id)

    def draft(self, draft_id: str) -> Draft | None:
        row = self.session.get(CeDraft, draft_id, populate_existing=True)   # the version may have moved in SQL
        if row is None:
            return None
        head = self.session.get(CeDraftVersion, (draft_id, row.version))
        if head is None:
            raise ContractViolation(SEMANTIC_INVALID, "draft head has no matching content snapshot")
        return Draft(row.id, row.workspace_id, row.definition_id, SchemaTypeRef(row.schema_type_id, row.schema_version),
                     row.authoring_locale, row.version, head.content, row.created_at, row.updated_at, row.schema_bundle)

    def advance_draft(self, draft_id: str, expected_version: int, content: object, *, author_user_id: int,
                      now: datetime) -> Draft:
        """Store ``content`` as the next version, only if the head is still ``expected_version``."""
        canonical = canonical_bytes(content)
        if type(expected_version) is not int or not 0 <= expected_version < 2**53 - 1:
            raise ContractViolation(SEMANTIC_INVALID, "draft version must be a nonnegative incrementable safe integer")
        moved = self.session.execute(
            update(CeDraft).where(CeDraft.id == draft_id, CeDraft.version == expected_version)
            .values(version=CeDraft.version + 1, updated_at=now)
            .execution_options(synchronize_session=False))
        if moved.rowcount != 1:
            current = self.draft(draft_id)
            if current is None:
                raise ContractViolation(SEMANTIC_INVALID, f"draft {draft_id} does not exist")
            require_draft_version(current, expected_version)
            raise ContractViolation(DRAFT_VERSION_CONFLICT, f"draft {draft_id} changed concurrently")
        self.session.add(CeDraftVersion(draft_id=draft_id, version=expected_version + 1, content=canonical,
                                        author_user_id=author_user_id, created_at=now))
        self.session.flush()
        return self.draft(draft_id)

    def draft_version_content(self, draft_id: str, version: int) -> bytes:
        row = self.session.get(CeDraftVersion, (draft_id, version))
        if row is None:
            raise ContractViolation(SEMANTIC_INVALID, f"draft {draft_id} has no version {version}")
        return row.content

    def revert_draft(self, draft_id: str, expected_version: int, to_version: int, *, author_user_id: int,
                     now: datetime) -> Draft:
        """Draft undo (§13): a new version restoring an earlier snapshot; history is kept."""
        restored = self.draft_version_content(draft_id, to_version)
        return self.advance_draft(draft_id, expected_version, parse_strict_json(restored),
                                  author_user_id=author_user_id, now=now)

    def append_answer(self, answer: DraftAnswer) -> None:
        self.draft_version_content(answer.draft_id, answer.draft_version)
        for value in (answer.answer, answer.mutations, answer.invalidated):
            if canonical_bytes(parse_strict_json(value)) != value:
                raise ContractViolation(SEMANTIC_INVALID, "decision log values must be canonical JSON")
        validate_definition("DraftAnswer", parse_strict_json(answer.answer), schema_id=REGISTRY_SCHEMA_ID)
        validate_definition("QuestionRef", {"questionId": answer.question_id, "questionVersion": answer.question_version},
                            schema_id=REGISTRY_SCHEMA_ID)
        self.session.add(CeDraftAnswer(
            draft_id=answer.draft_id, draft_version=answer.draft_version, question_id=answer.question_id,
            question_version=answer.question_version, answer=answer.answer, prompt_locale=answer.prompt_locale,
            author_user_id=answer.author_user_id, mutations=answer.mutations, invalidated=answer.invalidated,
            created_at=answer.created_at))
        self.session.flush()

    def answers(self, draft_id: str) -> tuple[DraftAnswer, ...]:
        rows = self.session.scalars(select(CeDraftAnswer).where(CeDraftAnswer.draft_id == draft_id)
                                    .order_by(CeDraftAnswer.id))
        return tuple(DraftAnswer(r.draft_id, r.draft_version, r.question_id, r.question_version, r.answer,
                                 r.prompt_locale, r.author_user_id, r.mutations, r.invalidated, r.created_at)
                     for r in rows)

    # --- execution locks (append-only, content-addressed) --------------------------------------

    def save_lock(self, lock: ExecutionLock, *, now: datetime) -> None:
        lock.validate_integrity()
        self._insert_once(CeExecutionLock,
                          {"lock_id": lock.lock_id, "digest": lock.digest, "canonical": lock.canonical, "created_at": now},
                          conflict_columns=["lock_id"])
        existing = self.session.get(CeExecutionLock, lock.lock_id, populate_existing=True)
        if existing.digest != lock.digest or existing.canonical != lock.canonical:
            raise ContractViolation(SEMANTIC_INVALID, f"lock {lock.lock_id} exists with different content")

    def lock(self, lock_id: str) -> ExecutionLock | None:
        row = self.session.get(CeExecutionLock, lock_id)
        if row is None:
            return None
        lock = ExecutionLock(row.lock_id, row.canonical, row.digest)
        lock.validate_integrity()
        return lock

    def _insert_once(self, model, values: dict, *, conflict_columns: list[str]) -> None:
        """Unique-key races are normal first-use requests, not failed transactions."""
        dialect = self.session.get_bind().dialect.name
        if dialect not in ("postgresql", "sqlite"):
            raise RuntimeError(f"unsupported content store dialect: {dialect}")
        insert = postgres_insert if dialect == "postgresql" else sqlite_insert
        self.session.execute(insert(model).values(**values).on_conflict_do_nothing(index_elements=conflict_columns))


def _definition(row: CeDefinition) -> Definition:
    return Definition(row.id, row.workspace_id, row.name, row.schema_type_id, row.created_at, row.tombstoned_at)
