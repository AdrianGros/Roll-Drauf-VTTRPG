"""Server-issued capabilities for independent table presentations."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class TableContext(db.Model):
    __tablename__ = "play_table_contexts"

    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    tab_hash = db.Column(db.String(64), nullable=False)
    auth_jti = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    mode = db.Column(db.String(8), nullable=False)
    socket_sid = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
