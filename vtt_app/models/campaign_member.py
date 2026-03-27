"""Campaign membership model (M2M User <-> Campaign)."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class CampaignMember(db.Model):
    """Campaign membership with role assignment per campaign."""

    __tablename__ = 'campaign_members'

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    campaign_role = db.Column(db.String(20), nullable=False)  # Player, DM, CO_DM, Observer
    status = db.Column(db.String(20), default='active')  # invited, active, left, kicked
    
    joined_at = db.Column(db.DateTime)
    invited_at = db.Column(db.DateTime, default=utcnow)
    accepted_at = db.Column(db.DateTime)
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'user_id', name='unique_campaign_member'),
    )

    campaign = db.relationship('Campaign', backref='member_records')
    user = db.relationship('User', backref='campaign_memberships', foreign_keys=[user_id])
    inviter = db.relationship('User', foreign_keys=[invited_by])

    def __repr__(self):
        return f'<CampaignMember campaign={self.campaign_id} user={self.user_id} role={self.campaign_role}>'

    def serialize(self):
        return {
            'user_id': self.user_id,
            'username': self.user.username,
            'campaign_role': self.campaign_role,
            'status': self.status,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None
        }

    def is_dm(self):
        """Check if this member is a DM in this campaign."""
        return str(self.campaign_role).upper() == 'DM'

    def is_co_dm(self):
        """Check if member has co-DM operator role."""
        return str(self.campaign_role).upper() in {'CO_DM', 'CODM'}

    def is_operator(self):
        """Check if member can operate session controls."""
        role = str(self.campaign_role).upper()
        return role in {'DM', 'CO_DM', 'CODM'}

    def is_observer(self):
        """Check if member is observer-only."""
        return str(self.campaign_role).upper() == 'OBSERVER'

    def is_active(self):
        """Check if member is actively in campaign."""
        return self.status == 'active'

    def accept_invite(self):
        """Accept campaign invitation."""
        self.status = 'active'
        self.joined_at = utcnow()
        self.accepted_at = utcnow()
        db.session.commit()
