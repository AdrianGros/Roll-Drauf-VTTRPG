"""Immutable playable Background/Feat publications, beside Eagle Species."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class CeRuleRevision(db.Model):
    __tablename__ = 'ce_rule_revisions'
    __table_args__ = (
        db.UniqueConstraint('scope_kind','scope_id','lineage','revision_number',name='uq_ce_rule_revision_number'),
        db.Index('ix_ce_rule_revision_scope','scope_kind','scope_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    scope_kind = db.Column(db.String(16), nullable=False)
    scope_id = db.Column(db.Integer, nullable=False)
    lineage = db.Column(db.String(240), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(16), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    source_uuid = db.Column(db.String(200), nullable=False)
    source_revision = db.Column(db.Integer, nullable=False)
    source_digest = db.Column(db.String(80), nullable=False)
    source = db.Column(db.JSON, nullable=False)
    supplement = db.Column(db.JSON, nullable=False)
    profile = db.Column(db.JSON, nullable=False)
    profile_digest = db.Column(db.String(80), nullable=False)
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    published_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def summary(self):
        return {'id':self.id,'kind':self.kind,'name':self.name,'revision':self.revision_number,
                'scope':{'kind':self.scope_kind,'id':self.scope_id},'sourceUuid':self.source_uuid,
                'sourceDigest':self.source_digest,'profileDigest':self.profile_digest}
