"""Per-campaign limits for the SRD character creator, set by the campaign's DM."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class CampaignSrdRules(db.Model):
    __tablename__ = 'campaign_srd_rules'

    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id', ondelete='CASCADE'), primary_key=True)
    ability_methods = db.Column(db.JSON, nullable=False, default=list)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
