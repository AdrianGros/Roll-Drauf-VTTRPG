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

    owner = db.relationship('User', backref='owned_campaigns', foreign_keys=[owner_id])
    members = db.relationship('CampaignMember', cascade='all, delete-orphan', lazy=True)
    sessions = db.relationship('GameSession', cascade='all, delete-orphan', lazy=True)

    # M17: Alias for consistency with M17 terminology
    @property
    def dm_id(self):
        """Alias for owner_id (owner is the DM)."""
        return self.owner_id

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

    def get_member(self, user_id):
        """Get campaign member by user_id."""
        from vtt_app.models import CampaignMember
        return CampaignMember.query.filter_by(campaign_id=self.id, user_id=user_id).first()

    # ===== M17: Team-View Methods =====

    @staticmethod
    def get_visible_campaigns(user):
        """
        Get campaigns visible to user.

        Logic:
        - Supporter+: All campaigns
        - DM/Headmaster: Own campaigns + joined campaigns
        - Player: Only joined campaigns
        """
        from vtt_app.models import CampaignMember, User

        if not user:
            return Campaign.query.filter(False)  # Empty

        # Platform staff see all
        if user.platform_role in ['supporter', 'moderator', 'admin', 'owner']:
            return Campaign.query.all()

        # DM/Headmaster see own campaigns
        own_campaigns = Campaign.query.filter_by(owner_id=user.id).all()

        # Plus campaigns they're members of
        member_campaigns = db.session.query(Campaign).join(
            CampaignMember,
            Campaign.id == CampaignMember.campaign_id
        ).filter(
            CampaignMember.user_id == user.id,
            CampaignMember.status == 'active'
        ).all()

        # Union (avoid duplicates)
        campaign_ids = set(c.id for c in own_campaigns + member_campaigns)
        return Campaign.query.filter(Campaign.id.in_(campaign_ids)).all()

    @staticmethod
    def get_team_campaigns(limit=100, offset=0, filter_dm=None, filter_status=None):
        """
        Get all campaigns for team dashboard (supporter+ only).

        Args:
            limit: Pagination limit
            offset: Pagination offset
            filter_dm: Filter by DM username
            filter_status: Filter by campaign status ('active', 'archived', 'paused')

        Returns:
            List of Campaign objects
        """
        from vtt_app.models import User

        query = Campaign.query

        if filter_dm:
            query = query.join(User, Campaign.owner_id == User.id).filter(
                User.username.ilike(f"%{filter_dm}%")
            )

        if filter_status:
            query = query.filter_by(status=filter_status)

        return query.order_by(Campaign.updated_at.desc()).limit(limit).offset(offset).all()
