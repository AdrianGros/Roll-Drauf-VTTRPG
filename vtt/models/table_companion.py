"""Stable session-local resource identity for an existing character companion."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class TableCompanionBinding(db.Model):
    __tablename__ = 'table_companion_bindings'
    __table_args__ = (
        db.UniqueConstraint('game_session_id', 'character_id', 'companion_id', name='uq_table_companion_source'),
    )
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False, index=True)
    companion_id = db.Column(db.String(80), nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey('token_states.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
