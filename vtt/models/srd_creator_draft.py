"""Draft of the SRD character creator, owned by one user until it is finalized."""

from vtt.extensions import db
from vtt.utils.time import utcnow


class SrdCreatorDraft(db.Model):
    """Server-side creator state. Becomes a `Character` exactly once (status 'finalized')."""

    __tablename__ = 'srd_creator_drafts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default='draft', index=True)  # draft | finalized | discarded
    version = db.Column(db.Integer, nullable=False, default=1)
    step = db.Column(db.String(32))
    name = db.Column(db.String(100))
    state = db.Column(db.JSON, nullable=False, default=dict)
    sources = db.Column(db.JSON, nullable=False, default=list)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    finalized_at = db.Column(db.DateTime)

    def summary(self):
        return {
            'id': self.id,
            'status': self.status,
            'version': self.version,
            'step': self.step,
            'name': self.name,
            'character_id': self.character_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
