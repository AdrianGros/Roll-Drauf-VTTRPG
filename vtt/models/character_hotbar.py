"""Personal declarative layouts and durable table command receipts."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class CharacterHotbar(db.Model):
    __tablename__ = "character_hotbars"
    __table_args__ = (db.UniqueConstraint("user_id", "character_id", name="uq_character_hotbar_user"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False, index=True)
    slots = db.Column(db.JSON, nullable=False, default=list)
    revision = db.Column(db.Integer, nullable=False, default=1)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class TableRequestReceipt(db.Model):
    __tablename__ = "table_request_receipts"
    __table_args__ = (db.UniqueConstraint("context_id", "request_id", name="uq_table_receipt_context_request"),)

    id = db.Column(db.Integer, primary_key=True)
    context_id = db.Column(db.Integer, db.ForeignKey("play_table_contexts.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    request_id = db.Column(db.String(120), nullable=False)
    request_digest = db.Column(db.String(64), nullable=False)
    response = db.Column(db.JSON)
    status_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
