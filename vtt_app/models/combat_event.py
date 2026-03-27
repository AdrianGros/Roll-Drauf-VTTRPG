"""Combat event model for append-only encounter log."""

from datetime import datetime

from vtt_app.extensions import db


class CombatEvent(db.Model):
    """Append-only event stream for encounter actions."""

    __tablename__ = "combat_events"

    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("combat_encounters.id"), nullable=False, index=True)
    sequence_no = db.Column(db.Integer, nullable=False)
    event_type = db.Column(db.String(40), nullable=False)

    actor_token_id = db.Column(db.Integer, db.ForeignKey("token_states.id"), index=True)
    target_token_id = db.Column(db.Integer, db.ForeignKey("token_states.id"), index=True)
    payload_json = db.Column(db.JSON, default=dict)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    encounter = db.relationship("CombatEncounter", backref=db.backref("events", lazy=True))
    actor_token = db.relationship("TokenState", foreign_keys=[actor_token_id])
    target_token = db.relationship("TokenState", foreign_keys=[target_token_id])
    creator = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("encounter_id", "sequence_no", name="uq_encounter_sequence"),
    )

    def __repr__(self):
        return f"<CombatEvent {self.id} encounter={self.encounter_id} type={self.event_type}>"

    def serialize(self):
        return {
            "id": self.id,
            "encounter_id": self.encounter_id,
            "sequence_no": self.sequence_no,
            "event_type": self.event_type,
            "actor_token_id": self.actor_token_id,
            "target_token_id": self.target_token_id,
            "payload_json": self.payload_json or {},
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
