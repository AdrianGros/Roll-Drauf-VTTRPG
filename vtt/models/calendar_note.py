"""Private calendar data. No campaign/table role grants access to another user's notes."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class CalendarNote(db.Model):
    __tablename__ = 'calendar_notes'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'request_key', name='uq_calendar_note_request'),
        db.CheckConstraint('revision >= 1', name='ck_calendar_note_revision'),
        db.CheckConstraint("color IN ('red','orange','yellow','green','teal','blue','purple')", name='ck_calendar_note_color'),
        db.CheckConstraint("reminder_state IN ('none','pending','ready','dismissed')", name='ck_calendar_note_reminder'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_key = db.Column(db.String(36), nullable=False)
    input_digest = db.Column(db.String(64), nullable=False)
    mutation_key = db.Column(db.String(36))
    mutation_digest = db.Column(db.String(64))
    local_date = db.Column(db.Date, nullable=False, index=True)
    title = db.Column(db.String(80), nullable=False)
    body = db.Column(db.String(2000), nullable=False, default='')
    color = db.Column(db.String(10), nullable=False, default='red')
    revision = db.Column(db.Integer, nullable=False, default=1)
    reminder_at = db.Column(db.DateTime, index=True)
    reminder_local = db.Column(db.String(16))
    timezone = db.Column(db.String(64), nullable=False, default='Europe/Berlin')
    fold = db.Column(db.Integer)
    reminder_state = db.Column(db.String(12), nullable=False, default='none', index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    deleted_at = db.Column(db.DateTime)


class CalendarOneShot(db.Model):
    __tablename__ = 'calendar_one_shots'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'request_key', name='uq_calendar_one_shot_request'),
    )
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, unique=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_key = db.Column(db.String(36), nullable=False)
    input_digest = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
