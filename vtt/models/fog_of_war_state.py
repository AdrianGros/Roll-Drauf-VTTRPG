"""S10: per-user, per-map Fog of War exploration state.

Scoped to (user, CampaignMap) -- S10 Apply decision #6: fog persists
across scene switches. A player who leaves a map and comes back later
(even in a different session using the same map) keeps what they
explored, matching Foundry's own per-user/per-scene persistence model.

Cells are stored as [col, row] grid-cell coordinates (a JSON array of
2-element lists), not a bitmap -- Apply decision #2: no image/canvas
dependency exists server-side in this stack, no client renders a fog
mask yet (explicitly deferred), and cell lists stay human-readable for
debugging a brand-new subsystem. A later slice can swap the storage
representation without changing the calculation contract in vision.py.
"""

from datetime import datetime

from vtt.extensions import db


class FogOfWarState(db.Model):
    __tablename__ = "fog_of_war_state"
    __table_args__ = (
        db.UniqueConstraint("user_id", "campaign_map_id", name="uq_fog_user_map"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    campaign_map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)

    # Cumulative: every cell ever seen. Only grows (until an explicit
    # reset) -- exploring never un-explores.
    explored_cells = db.Column(db.JSON, default=list, nullable=False)
    # This tick's snapshot: what is visible right now. Recomputed on every
    # relevant recalculation, unlike explored_cells.
    visible_cells = db.Column(db.JSON, default=list, nullable=False)

    version = db.Column(db.Integer, default=1, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User")
    campaign_map = db.relationship("CampaignMap")

    def __repr__(self):
        return f"<FogOfWarState user={self.user_id} map={self.campaign_map_id} v{self.version}>"

    def serialize(self):
        return {
            "user_id": self.user_id,
            "campaign_map_id": self.campaign_map_id,
            "explored_cells": self.explored_cells or [],
            "visible_cells": self.visible_cells or [],
            "version": self.version,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
