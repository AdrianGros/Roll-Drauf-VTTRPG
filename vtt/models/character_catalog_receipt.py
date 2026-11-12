"""Bounded 24h receipts for owner-authorized catalog additions outside a table context."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class CharacterCatalogReceipt(db.Model):
    __tablename__ = 'character_catalog_receipts'
    __table_args__ = (
        db.UniqueConstraint('character_id', 'actor_user_id', 'request_id', name='uq_character_catalog_request'),
    )
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_id = db.Column(db.String(36), nullable=False)
    request_digest = db.Column(db.String(64), nullable=False)
    response = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
