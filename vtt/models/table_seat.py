"""Table seat of a campaign operator for one session (Tischplatz).

A DM or CO-DM may sit at a session's table as a player. Only that choice is
stored; without a row the campaign role applies. A row never raises rights:
vtt.play.service.get_table_role lowers an operator to PLAYER while it exists.
"""

from vtt.extensions import db
from vtt.utils.time import utcnow

PLAYER_SEAT = "player"


class TableSeat(db.Model):
    __tablename__ = "table_seats"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seat = db.Column(db.String(16), nullable=False, default=PLAYER_SEAT)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.UniqueConstraint("game_session_id", "user_id", name="uq_table_seat_session_user"),
    )
