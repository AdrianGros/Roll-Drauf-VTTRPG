"""Calendar recurrence definitions and durable links to real game sessions."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class SessionSeries(db.Model):
    __tablename__ = 'session_series'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'created_by', 'request_key'),
        db.CheckConstraint("frequency IN ('once','weekly','biweekly','monthly')"),
        db.CheckConstraint("status IN ('active','stopped')"),
    )
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_key = db.Column(db.String(36), nullable=False)
    input_digest = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    first_local = db.Column(db.DateTime, nullable=False)
    timezone = db.Column(db.String(64), nullable=False)
    frequency = db.Column(db.String(12), nullable=False)
    until_date = db.Column(db.Date)
    duration_minutes = db.Column(db.Integer)
    status = db.Column(db.String(12), nullable=False, default='active')
    next_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def serialize(self):
        return dict(id=self.id, name=self.name, frequency=self.frequency,
                    first_local=self.first_local.isoformat(timespec='minutes'),
                    timezone=self.timezone, until=self.until_date.isoformat() if self.until_date else None,
                    duration_minutes=self.duration_minutes, status=self.status)


class SessionOccurrence(db.Model):
    __tablename__ = 'session_occurrences'
    __table_args__ = (db.UniqueConstraint('series_id', 'ordinal'),)
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('session_series.id'), nullable=False, index=True)
    ordinal = db.Column(db.Integer, nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, unique=True)
