"""Additive UI/playtable state; campaign hierarchy and per-session initiative rounds."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class MapViewSettings(db.Model):
    __tablename__ = 'map_view_settings'
    map_id = db.Column(db.Integer, db.ForeignKey('campaign_maps.id'), primary_key=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    grid_visible = db.Column(db.Boolean, nullable=False, default=True)
    dynamic_lighting = db.Column(db.Boolean, nullable=False, default=True)
    ambient = db.Column(db.Integer, nullable=False, default=25)


class PageHierarchyState(db.Model):
    __tablename__ = 'page_hierarchy_states'
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), primary_key=True)
    revision = db.Column(db.Integer, nullable=False, default=1)


class MapPageParent(db.Model):
    __tablename__ = 'map_page_parents'
    map_id = db.Column(db.Integer, db.ForeignKey('campaign_maps.id'), primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    parent_map_id = db.Column(db.Integer, db.ForeignKey('campaign_maps.id'), nullable=True)
    order_index = db.Column(db.Integer, nullable=False, default=0)


class InitiativeRound(db.Model):
    __tablename__ = 'initiative_rounds'
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), primary_key=True)
    number = db.Column(db.Integer, nullable=False, default=1)
    revision = db.Column(db.Integer, nullable=False, default=1)


class InitiativeCandidate(db.Model):
    __tablename__ = 'initiative_candidates'
    __table_args__ = (db.UniqueConstraint('session_id', 'round_number', 'event_id', name='uq_initiative_candidate_event'),)
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    round_number = db.Column(db.Integer, nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey('token_states.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.String(160), nullable=False)
    source = db.Column(db.String(30), nullable=False, default='roll')
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    decided_by = db.Column(db.Integer, db.ForeignKey('users.id'))
