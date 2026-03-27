"""Game session model for D&D sessions (one session = one night/meeting)."""

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
    duration_minutes = db.Column(db.Integer)  # Expected duration
    
    map_id = db.Column(db.Integer, db.ForeignKey('campaign_maps.id'), nullable=True, index=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, ready, in_progress, paused, completed/ended, cancelled
    
    session_log = db.Column(db.Text)  # Notes/summary
    xp_earned = db.Column(db.Integer, default=0)
    treasure_log = db.Column(db.JSON)  # {gold: X, items: [...]}
    
    created_at = db.Column(db.DateTime, default=utcnow)

    campaign = db.relationship('Campaign', backref='game_sessions')
    active_map = db.relationship('CampaignMap', foreign_keys=[map_id])

    def __repr__(self):
        return f'<GameSession {self.name} campaign={self.campaign_id}>'

    def serialize(self):
        runtime_status = self.get_runtime_status()
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'name': self.name,
            'map_id': self.map_id,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'status': self.status,
            'runtime_status': runtime_status,
            'duration_minutes': self.duration_minutes
        }

    def is_active(self):
        """Check if session is currently in progress."""
        return self.status == 'in_progress'

    def get_runtime_status(self):
        """Return normalized runtime status for play surface compatibility."""
        status = str(self.status or "").strip().lower()
        if status == "completed":
            return "ended"
        if status == "cancelled":
            return "paused"
        return status or "scheduled"

    def start(self):
        """Mark session as started."""
        self.status = 'in_progress'
        self.started_at = utcnow()
        db.session.commit()

    def end(self):
        """Mark session as completed."""
        self.status = 'completed'
        self.ended_at = utcnow()
        db.session.commit()
