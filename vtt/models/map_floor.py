"""Private map artwork. These rows deliberately are not campaign Assets."""
from datetime import datetime
from vtt.extensions import db


class MapFloorDeck(db.Model):
    __tablename__ = "map_floor_decks"
    map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), primary_key=True)
    revision = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    # Validated against live images of this map in the mutation transaction.
    active_floor_id = db.Column(db.Integer)


class MapFloorImage(db.Model):
    __tablename__ = "map_floor_images"
    __table_args__ = (db.UniqueConstraint("map_id", "request_id", name="uq_map_floor_request"),)
    id = db.Column(db.Integer, primary_key=True)
    map_id = db.Column(db.Integer, db.ForeignKey("campaign_maps.id"), nullable=False, index=True)
    order_index = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    reveal_below = db.Column(db.Boolean, nullable=False, default=False)
    openings = db.Column(db.JSON, nullable=False, default=list)
    storage_key = db.Column(db.String(512), nullable=False)
    storage_provider = db.Column(db.String(20), nullable=False)
    png_sha256 = db.Column(db.String(64), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    request_id = db.Column(db.String(80), nullable=False)
    input_digest = db.Column(db.String(64), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Keep a small deduplication tombstone after releasing storage/quota.
    deleted_at = db.Column(db.DateTime)

    def configuration(self):
        return dict(id=self.id, name=self.name, order_index=self.order_index,
                    reveal_below=self.reveal_below, openings=self.openings,
                    width=self.width, height=self.height, size_bytes=self.size_bytes)
