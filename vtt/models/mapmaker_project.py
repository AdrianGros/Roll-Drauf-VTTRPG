"""Private, editable Mapmaker projects; imported by the Mapmaker blueprint."""

from datetime import datetime
import uuid

from vtt.extensions import db


class MapmakerProject(db.Model):
    __tablename__ = "mapmaker_projects"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(80), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    storage_key = db.Column(db.String(250), nullable=False, unique=True)
    storage_provider = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def serialize(self):
        return {
            "id": self.id, "title": self.title, "width": self.width,
            "height": self.height, "revision": self.revision,
            "sizeBytes": self.size_bytes,
            "createdAt": self.created_at.isoformat() + "Z",
            "updatedAt": self.updated_at.isoformat() + "Z",
        }
