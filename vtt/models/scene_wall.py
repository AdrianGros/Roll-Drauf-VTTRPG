"""S10: a sight/light-blocking line segment on a map.

Keyed to CampaignMap (not SceneStack/SceneLayer): a wall is geometry
belonging to the map image itself, the same anchor TokenState already
uses (token.map_id), not to a particular session's arrangement of layers
around that map.
"""

from datetime import datetime

from vtt.extensions import db

SIGHT_VALUES = {"normal", "limited", "none", "proximity"}
LIGHT_VALUES = {"normal", "ethereal", "none"}


class SceneWall(db.Model):
    __tablename__ = "scene_walls"

    id = db.Column(db.Integer, primary_key=True)
    campaign_map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)

    x0 = db.Column(db.Integer, nullable=False)
    y0 = db.Column(db.Integer, nullable=False)
    x1 = db.Column(db.Integer, nullable=False)
    y1 = db.Column(db.Integer, nullable=False)

    # S10 Apply decision: the research doc's full Foundry-parity semantics
    # (limited = see-past-one-not-two, proximity = distance-graded) are
    # deferred -- vision.py treats "limited" and "proximity" as fully
    # sight-blocking for now, same as "normal". The column already carries
    # the real value so a later slice can refine the calculation without a
    # second migration.
    sight = db.Column(db.String(20), default="normal", nullable=False)
    # Ethereal blocks sight/light identically to normal in this engine --
    # the distinction (tokens can physically pass through) has no effect
    # here since this app does not compute movement collision.
    light = db.Column(db.String(20), default="normal", nullable=False)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    campaign_map = db.relationship("CampaignMap")
    creator = db.relationship("User")

    def blocks_sight(self) -> bool:
        return self.sight != "none"

    def __repr__(self):
        return f"<SceneWall {self.id} map={self.campaign_map_id}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_map_id": self.campaign_map_id,
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "sight": self.sight,
            "light": self.light,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
