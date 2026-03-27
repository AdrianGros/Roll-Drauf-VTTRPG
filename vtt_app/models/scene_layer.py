"""Scene layer model for vertical map/floor structures."""

from datetime import datetime

from vtt_app.extensions import db


class SceneLayer(db.Model):
    """Single layer/floor inside a scene stack."""

    __tablename__ = "scene_layers"

    id = db.Column(db.Integer, primary_key=True)
    scene_stack_id = db.Column(db.Integer, db.ForeignKey("scene_stacks.id"), nullable=False, index=True)
    campaign_map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_player_visible = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    scene_stack = db.relationship("SceneStack", backref="layers")
    campaign_map = db.relationship("CampaignMap")

    __table_args__ = (
        db.UniqueConstraint("scene_stack_id", "campaign_map_id", name="uq_scene_layer_stack_map"),
    )

    def __repr__(self):
        return f"<SceneLayer {self.id} stack={self.scene_stack_id} order={self.order_index}>"

    def serialize(self):
        return {
            "id": self.id,
            "scene_stack_id": self.scene_stack_id,
            "campaign_map_id": self.campaign_map_id,
            "label": self.label,
            "order_index": self.order_index,
            "is_player_visible": self.is_player_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "campaign_map": self.campaign_map.serialize() if self.campaign_map else None,
        }
