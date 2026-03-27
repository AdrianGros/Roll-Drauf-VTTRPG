"""Campaign model for D&D campaigns."""

from datetime import datetime
from vtt_app.extensions import db


class Campaign(db.Model):
    """Campaign entity - D&D campaign with DM and players."""

    __tablename__ = 'campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='active')  # active, paused, archived
    max_players = db.Column(db.Integer, default=6)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)  # Soft delete for GDPR

    owner = db.relationship('User', backref='owned_campaigns')
    members = db.relationship('CampaignMember', cascade='all, delete-orphan', lazy=True)
    sessions = db.relationship('GameSession', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<Campaign {self.name}>'

    def serialize(self, include_members=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner': self.owner.username,
            'status': self.status,
            'max_players': self.max_players,
            'created_at': self.created_at.isoformat()
        }
        if include_members:
            data['members'] = [m.serialize() for m in self.members if m.status != 'kicked']
        return data

    def is_public(self):
        """Check if campaign is public (not deleted)."""
        return self.deleted_at is None

    def get_active_members(self):
        """Get all active members (not kicked, not invited)."""
        return [m for m in self.members if m.status == 'active']

    def get_player_count(self):
        """Get count of active members."""
        return len(self.get_active_members())

    def can_add_player(self):
        """Check if campaign has room for more players."""
        return self.get_player_count() < self.max_players
