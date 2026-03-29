"""Game session model for D&D sessions (one session = one night/meeting)."""

from datetime import timedelta
from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class GameSession(db.Model):
    """A single D&D session (gaming night) within a campaign."""

    __tablename__ = 'game_sessions'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)

    scheduled_at = db.Column(db.DateTime, index=True)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    paused_at = db.Column(db.DateTime)  # M41: Track when session was paused
    duration_minutes = db.Column(db.Integer)  # Expected duration

    map_id = db.Column(db.Integer, db.ForeignKey('campaign_maps.id'), nullable=True, index=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, ready, in_progress, paused, completed/ended, cancelled

    # M41: Enhanced state machine fields
    session_state = db.Column(db.String(20), default='preparing')  # preparing, active, paused, ended
    player_limit = db.Column(db.Integer, default=6)
    current_players_count = db.Column(db.Integer, default=0)
    session_password = db.Column(db.String(100), nullable=True)  # Optional password protection
    is_archived = db.Column(db.Boolean, default=False, index=True)  # For archival after 30d

    session_log = db.Column(db.Text)  # Notes/summary
    xp_earned = db.Column(db.Integer, default=0)
    treasure_log = db.Column(db.JSON)  # {gold: X, items: [...]}

    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    campaign = db.relationship('Campaign', backref='game_sessions')
    active_map = db.relationship('CampaignMap', foreign_keys=[map_id])

    def __repr__(self):
        return f'<GameSession {self.name} campaign={self.campaign_id}>'

    def serialize(self):
        """Return JSON-safe dict."""
        runtime_status = self.get_runtime_status()
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'name': self.name,
            'map_id': self.map_id,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'status': self.status,
            'session_state': self.session_state,
            'runtime_status': runtime_status,
            'duration_minutes': self.duration_minutes,
            'player_limit': self.player_limit,
            'current_players_count': self.current_players_count,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def is_active(self):
        """Check if session is currently in progress."""
        return self.session_state == 'active'

    def get_runtime_status(self):
        """Return normalized runtime status for play surface compatibility."""
        status = str(self.status or "").strip().lower()
        if status == "completed":
            return "ended"
        if status == "cancelled":
            return "paused"
        return status or "scheduled"

    # M41: State machine methods
    def can_transition_to(self, target_state):
        """
        Check if transition to target_state is valid.

        Valid transitions:
        - preparing → active
        - active ↔ paused
        - any → ended
        - any → archived (after 30 days)
        """
        current = self.session_state
        valid_transitions = {
            'preparing': ['active', 'ended', 'archived'],
            'active': ['paused', 'ended', 'archived'],
            'paused': ['active', 'ended', 'archived'],
            'ended': ['archived'],
            'archived': [],
        }
        return target_state in valid_transitions.get(current, [])

    def start(self):
        """
        Transition session to active state (M41).

        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition_to('active'):
            raise ValueError(f"Cannot transition from {self.session_state} to active")

        self.session_state = 'active'
        self.status = 'in_progress'
        self.started_at = utcnow()
        self.paused_at = None
        db.session.commit()

    def pause(self):
        """
        Pause an active session (M41).

        Raises:
            ValueError: If session is not active
        """
        if self.session_state != 'active':
            raise ValueError("Can only pause active sessions")

        self.session_state = 'paused'
        self.status = 'paused'
        self.paused_at = utcnow()
        db.session.commit()

    def resume(self):
        """
        Resume a paused session (M41).

        Raises:
            ValueError: If session is not paused
        """
        if self.session_state != 'paused':
            raise ValueError("Can only resume paused sessions")

        self.session_state = 'active'
        self.status = 'in_progress'
        self.paused_at = None
        db.session.commit()

    def end(self):
        """
        End the session and transition to ended state (M41).
        """
        if not self.can_transition_to('ended'):
            raise ValueError(f"Cannot end session in state {self.session_state}")

        self.session_state = 'ended'
        self.status = 'completed'
        self.ended_at = utcnow()
        db.session.commit()

    def archive(self):
        """
        Archive the session (M41).
        Can be called after 30 days of session completion.
        """
        if not self.can_transition_to('archived'):
            raise ValueError(f"Cannot archive session in state {self.session_state}")

        self.session_state = 'archived'
        self.is_archived = True
        db.session.commit()

    def should_auto_archive(self):
        """Check if session should be auto-archived (30+ days old)."""
        if self.session_state == 'archived':
            return False
        if self.session_state != 'ended' or not self.ended_at:
            return False
        age_days = (utcnow() - self.ended_at).days
        return age_days >= 30
