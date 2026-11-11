"""Optional physical calibration; map grid geometry stays in pixels."""
from vtt.extensions import db
from vtt.utils.time import utcnow


class CampaignMapScale(db.Model):
    __tablename__='campaign_map_scales'
    map_id=db.Column(db.Integer,db.ForeignKey('campaign_maps.id'),primary_key=True)
    meters_per_square=db.Column(db.Numeric(12,4))
    revision=db.Column(db.Integer,nullable=False,default=1)
    updated_by=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    updated_at=db.Column(db.DateTime,nullable=False,default=utcnow,onupdate=utcnow)

    def serialize(self):
        return {'revision':self.revision,'meters_per_square':float(self.meters_per_square) if self.meters_per_square is not None else None}


def scale_for(map_id):
    row=db.session.get(CampaignMapScale,map_id)
    return row.serialize() if row else {'revision':0,'meters_per_square':None}
