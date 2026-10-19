"""SQLAlchemy models for the WP3 content tables (G1 plan §7; migration m73).

Content, provenance and logs are stored as canonical bytes rather than JSON
columns: PostgreSQL jsonb normalizes documents, and the digests identify exact
bytes (§6). Revisions, draft versions, the decision log and locks are
append-only; m73 adds PostgreSQL triggers that reject UPDATE and DELETE on them.
These models are not imported by the running app until the transports are
wired behind feature flags (WP4).
"""

from vtt.extensions import db


class CeWorkspace(db.Model):
    __tablename__ = "ce_workspaces"

    id = db.Column(db.String(128), primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeDefinition(db.Model):
    __tablename__ = "ce_definitions"

    id = db.Column(db.String(128), primary_key=True)
    workspace_id = db.Column(db.String(128), db.ForeignKey("ce_workspaces.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    schema_type_id = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    tombstoned_at = db.Column(db.DateTime(timezone=True))


class CeRevision(db.Model):
    __tablename__ = "ce_revisions"

    id = db.Column(db.String(128), primary_key=True)
    definition_id = db.Column(db.String(128), db.ForeignKey("ce_definitions.id"), nullable=False, index=True)
    schema_type_id = db.Column(db.String(128), nullable=False)
    schema_version = db.Column(db.BigInteger, nullable=False)
    canonical = db.Column(db.LargeBinary, nullable=False)
    digest = db.Column(db.String(71), nullable=False, index=True)
    provenance = db.Column(db.LargeBinary, nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeDraft(db.Model):
    __tablename__ = "ce_drafts"

    id = db.Column(db.String(128), primary_key=True)
    workspace_id = db.Column(db.String(128), db.ForeignKey("ce_workspaces.id"), nullable=False, index=True)
    definition_id = db.Column(db.String(128), db.ForeignKey("ce_definitions.id"))
    schema_type_id = db.Column(db.String(128), nullable=False)
    schema_version = db.Column(db.BigInteger, nullable=False)
    authoring_locale = db.Column(db.String(8), nullable=False)
    schema_bundle = db.Column(db.LargeBinary, nullable=False)
    version = db.Column(db.BigInteger, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeDraftVersion(db.Model):
    __tablename__ = "ce_draft_versions"

    draft_id = db.Column(db.String(128), db.ForeignKey("ce_drafts.id"), primary_key=True)
    version = db.Column(db.BigInteger, primary_key=True)
    content = db.Column(db.LargeBinary, nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeDraftAnswer(db.Model):
    __tablename__ = "ce_draft_answers"
    __table_args__ = (
        db.ForeignKeyConstraint(["draft_id", "draft_version"], ["ce_draft_versions.draft_id", "ce_draft_versions.version"]),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    draft_id = db.Column(db.String(128), db.ForeignKey("ce_drafts.id"), nullable=False, index=True)
    draft_version = db.Column(db.BigInteger, nullable=False)
    question_id = db.Column(db.String(128), nullable=False)
    question_version = db.Column(db.BigInteger, nullable=False)
    answer = db.Column(db.LargeBinary, nullable=False)
    prompt_locale = db.Column(db.String(8), nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mutations = db.Column(db.LargeBinary, nullable=False)
    invalidated = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


class CeExecutionLock(db.Model):
    __tablename__ = "ce_execution_locks"

    lock_id = db.Column(db.String(128), primary_key=True)
    digest = db.Column(db.String(71), nullable=False, unique=True)
    canonical = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)


CONTENT_TABLES = (CeWorkspace.__table__, CeDefinition.__table__, CeRevision.__table__, CeDraft.__table__,
                  CeDraftVersion.__table__, CeDraftAnswer.__table__, CeExecutionLock.__table__)
