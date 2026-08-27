"""S10: a light or darkness source on a map, keyed to CampaignMap for the
same reason as SceneWall (geometry belongs to the map, not a session's
layer arrangement of it)."""

from datetime import datetime

from vtt.extensions import db

LIGHT_TYPES = {"light", "darkness"}


class SceneLight(db.Model):
    __tablename__ = "scene_lights"

    id = db.Column(db.Integer, primary_key=True)
    campaign_map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)

    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    bright_radius = db.Column(db.Integer, default=0, nullable=False)
    dim_radius = db.Column(db.Integer, default=0, nullable=False)
    color = db.Column(db.String(20), default="#ffffff")
    # Foundry's "vision provision" toggle: whether a token that can
    # otherwise see TOWARD this light's area (unobstructed by walls from
    # the token's own position) can see INTO it even past the token's own
    # sight_range. See vtt/play/vision.py's module docstring for the full
    # simplified model this engine actually computes.
    provides_vision = db.Column(db.Boolean, default=True, nullable=False)
    light_type = db.Column(db.String(20), default="light", nullable=False)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    campaign_map = db.relationship("CampaignMap")
    creator = db.relationship("User")

    def max_radius(self) -> int:
        return max(self.bright_radius or 0, self.dim_radius or 0)

    def __repr__(self):
        return f"<SceneLight {self.id} map={self.campaign_map_id} type={self.light_type}>"

    def serialize(self):
        return {
            "id": self.id,
            "campaign_map_id": self.campaign_map_id,
            "x": self.x,
            "y": self.y,
            "bright_radius": self.bright_radius,
            "dim_radius": self.dim_radius,
            "color": self.color,
            "provides_vision": self.provides_vision,
            "light_type": self.light_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
