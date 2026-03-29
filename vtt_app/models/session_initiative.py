"""M43: Session initiative tracker for combat turn order."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class SessionInitiative(db.Model):
    """Initiative entry for a character in combat (M43).

    Tracks initiative roll order and current turn in session.
    """

    __tablename__ = 'session_initiative'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=True, index=True)

    character_name = db.Column(db.String(100), nullable=False)  # For NPCs without character_id
    initiative_roll = db.Column(db.Integer, nullable=False)
    turn_order = db.Column(db.Integer, nullable=False)  # Position in initiative order (0-based)

    is_current_turn = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    session = db.relationship('GameSession', backref='initiative_order', lazy=True)
    character = db.relationship('Character', backref='session_initiatives', lazy=True)

    __table_args__ = (
        db.Index('idx_session_initiative_order', 'session_id', 'turn_order'),
    )

    def __repr__(self):
        return f'<SessionInitiative {self.character_name} roll={self.initiative_roll} order={self.turn_order}>'

    def serialize(self):
        """Return JSON-safe dict."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'character_id': self.character_id,
            'character_name': self.character_name,
            'initiative_roll': self.initiative_roll,
            'turn_order': self.turn_order,
            'is_current_turn': self.is_current_turn,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def advance_turn(self):
        """
        Mark next turn in initiative order.

        Updates current turn flag and advances turn_order.
        Wraps around to beginning of order when reaching end.
        """
        # Get all initiatives in session, ordered
        all_initiatives = SessionInitiative.query.filter_by(session_id=self.session_id).order_by(
            SessionInitiative.turn_order
        ).all()

        if not all_initiatives:
            return

        # Clear current turn on all
        for init in all_initiatives:
            init.is_current_turn = False

        # Get next turn (wrap around)
        max_turn = len(all_initiatives) - 1
        next_turn = (self.turn_order + 1) % (max_turn + 1)

        # Mark next as current
        next_initiative = next((i for i in all_initiatives if i.turn_order == next_turn), None)
        if next_initiative:
            next_initiative.is_current_turn = True

        db.session.commit()

    @staticmethod
    def get_session_initiative(session_id):
        """Get initiative order for session."""
        return SessionInitiative.query.filter_by(session_id=session_id).order_by(
            SessionInitiative.turn_order
        ).all()

    @staticmethod
    def get_current_turn(session_id):
        """Get the character whose turn it is."""
        return SessionInitiative.query.filter_by(
            session_id=session_id,
            is_current_turn=True
        ).first()

    @staticmethod
    def reset_initiative(session_id):
        """Clear all initiative entries for a session."""
        SessionInitiative.query.filter_by(session_id=session_id).delete()
        db.session.commit()
