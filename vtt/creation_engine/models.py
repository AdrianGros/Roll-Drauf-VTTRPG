"""Storage for documents written by the Creation Engine's Eagle Homebrew editor.

One row is one Foundry-shaped document. A Library row lives in the author's personal Eagle Library
(`scope_kind="library"`, `scope_id` = user id, `pack` = "world.eagle-<key>[-<rules>]"). A world row lives in
the world the editor was opened for: a campaign the user leads (`"campaign"`) or the user's personal workshop
(`"personal"`); world rows have an empty `pack`. `source` is the complete document JSON, exactly as the
editor wrote it.
"""

from datetime import datetime, timezone

from vtt.extensions import db


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CeEagleDocument(db.Model):
    __tablename__ = "ce_eagle_documents"
    __table_args__ = (
        db.UniqueConstraint("scope_kind", "scope_id", "pack", "document_name", "document_id",
                            name="uq_ce_eagle_documents_identity"),
        db.Index("ix_ce_eagle_documents_scope", "scope_kind", "scope_id", "document_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    scope_kind = db.Column(db.String(16), nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)
    pack = db.Column(db.String(64), nullable=False, default="")
    document_name = db.Column(db.String(16), nullable=False)
    document_id = db.Column(db.String(64), nullable=False)
    doc_type = db.Column(db.String(32))
    name = db.Column(db.String(200), nullable=False)
    source = db.Column(db.JSON, nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=_now, onupdate=_now)

    @property
    def uuid(self):
        if self.pack:
            return f"Compendium.{self.pack}.{self.document_name}.{self.document_id}"
        return f"{self.document_name}.{self.document_id}"

    def summary(self):
        return {"uuid": self.uuid, "pack": self.pack or None, "documentName": self.document_name,
                "type": self.doc_type, "name": self.name, "revision": self.revision,
                "updatedAt": self.updated_at.isoformat() if self.updated_at else None}
