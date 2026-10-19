"""Race-to-sheet associations and idempotent handoff results (M79)."""

from vtt.extensions import db


class CeCharacterOrigin(db.Model):
    __tablename__ = "ce_character_origins"
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), primary_key=True)
    revision_id = db.Column(db.String(128), db.ForeignKey("ce_revisions.id"), nullable=False)
    version = db.Column(db.BigInteger, nullable=False)


class CeSheetCommand(db.Model):
    __tablename__ = "ce_sheet_commands"
    principal_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    idempotency_key = db.Column(db.String(128), primary_key=True)
    request_digest = db.Column(db.String(71), nullable=False)
    result = db.Column(db.LargeBinary, nullable=False)


SHEET_TABLES = (CeCharacterOrigin.__table__, CeSheetCommand.__table__)
