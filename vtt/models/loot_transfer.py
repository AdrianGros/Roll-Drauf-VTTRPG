"""S09: the loot-transfer idempotency + audit record.

CRITICAL risk in the research doc: a network retry must never duplicate a
transfer. idempotency_key is UNIQUE -- a second request with the same key
finds this row and returns its cached items_transferred instead of moving
anything a second time. This table doubles as the audit log the doc also
calls for (session_id/actor/source/recipient/items, one row per real
transfer), so there is no separate audit table to keep in sync."""

from datetime import datetime

from vtt.extensions import db


class LootTransfer(db.Model):
    __tablename__ = "loot_transfers"

    id = db.Column(db.Integer, primary_key=True)
    idempotency_key = db.Column(db.String(120), nullable=False, unique=True, index=True)

    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    source_token_id = db.Column(db.Integer, db.ForeignKey("token_states.id"), nullable=False)
    recipient_character_id = db.Column(db.Integer, db.ForeignKey("characters.id"), nullable=False)

    # [{"name": str, "quantity": int}, ...] -- a snapshot, not a live FK
    # relation, so the audit trail survives the source items later being
    # fully depleted/deleted.
    items_transferred = db.Column(db.JSON, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    actor = db.relationship("User")
    source_token = db.relationship("TokenState")
    recipient_character = db.relationship("Character")

    def __repr__(self):
        return f"<LootTransfer {self.id} session={self.game_session_id} key={self.idempotency_key}>"

    def serialize(self):
        return {
            "id": self.id,
            "idempotency_key": self.idempotency_key,
            "source_token_id": self.source_token_id,
            "recipient_character_id": self.recipient_character_id,
            "recipient_character_name": self.recipient_character.name if self.recipient_character else None,
            "items_transferred": self.items_transferred,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
