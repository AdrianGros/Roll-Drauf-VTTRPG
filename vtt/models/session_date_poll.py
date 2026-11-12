"""Additive date-poll tables: a poll proposes UTC start times for one unstarted session.

Authorization is never stored here; every route rechecks the campaign, the
session and the poll->option chain. ``selected_option_id`` is deliberately a
plain integer (no foreign key) so the three tables have no circular DDL and can
be created in a fixed order by the additive migration; the service verifies that
it always names an option of the same poll while holding the campaign lock.
"""
from sqlalchemy import text

from vtt.extensions import db
from vtt.utils.time import utcnow

POLL_STATUSES = ('open', 'closed', 'cancelled')
VOTE_VALUES = ('yes', 'maybe', 'no')


class SessionDatePoll(db.Model):
    __tablename__ = 'session_date_polls'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'created_by', 'request_key', name='uq_session_date_poll_request'),
        db.CheckConstraint("status IN ('open','closed','cancelled')", name='ck_session_date_poll_status'),
        # Defense in depth for the campaign-lock rule "at most one open poll per session".
        db.Index('uq_session_date_poll_one_open', 'session_id', unique=True,
                 postgresql_where=text("status = 'open'"), sqlite_where=text("status = 'open'")),
    )
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_key = db.Column(db.String(36), nullable=False)
    input_digest = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(12), nullable=False, default='open')
    revision = db.Column(db.Integer, nullable=False, default=1)
    selected_option_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    closed_at = db.Column(db.DateTime)

    options = db.relationship('SessionDateOption', order_by='SessionDateOption.starts_at',
                              cascade='all, delete-orphan', lazy='select')


class SessionDateOption(db.Model):
    __tablename__ = 'session_date_options'
    __table_args__ = (
        db.UniqueConstraint('poll_id', 'starts_at', name='uq_session_date_option_start'),
        db.CheckConstraint('duration_minutes IS NULL OR (duration_minutes >= 1 AND duration_minutes <= 1440)',
                           name='ck_session_date_option_duration'),
    )
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('session_date_polls.id'), nullable=False, index=True)
    starts_at = db.Column(db.DateTime, nullable=False)  # naive UTC, like GameSession.scheduled_at
    duration_minutes = db.Column(db.Integer)

    votes = db.relationship('SessionDateVote', cascade='all, delete-orphan', lazy='select')


class SessionDateVote(db.Model):
    __tablename__ = 'session_date_votes'
    __table_args__ = (
        db.UniqueConstraint('option_id', 'user_id', name='uq_session_date_vote_user'),
        db.CheckConstraint("value IN ('yes','maybe','no')", name='ck_session_date_vote_value'),
    )
    id = db.Column(db.Integer, primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey('session_date_options.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    value = db.Column(db.String(8), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
