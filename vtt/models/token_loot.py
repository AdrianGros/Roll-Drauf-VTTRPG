"""S09: items sitting on a lootable token (corpse, chest), distinct from
character-owned InventoryItem -- the research doc's own Lessons Learned
explicitly warns against overloading InventoryItem or TokenState.metadata_json
for this; a real relation also makes the atomic quantity decrements loot
transfer needs (see loot_transfer.py) far safer than a JSON blob would."""

from datetime import datetime

from vtt.extensions import db


class TokenLoot(db.Model):
    """An item stack available on a token flagged TokenState.is_loot_source."""

    __tablename__ = "token_loot"

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey("token_states.id"), nullable=False, index=True)

    name = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1, nullable=False)
    weight_per_unit = db.Column(db.Float)
    cost = db.Column(db.String(50))
    is_consumable = db.Column(db.Boolean, default=False, nullable=False)
    # S09 Apply decision: cursed items transfer freely with no special-case
    # logic this slice (research doc section 8, explicit deferral) -- the
    # flag is carried through so a later slice can add handling without a
    # second migration.
    is_cursed = db.Column(db.Boolean, default=False, nullable=False)
    description = db.Column(db.Text)
    effects = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    token = db.relationship("TokenState")

    def __repr__(self):
        return f"<TokenLoot {self.name} x{self.quantity} token={self.token_id}>"

    def serialize(self):
        return {
            "id": self.id,
            "token_id": self.token_id,
            "name": self.name,
            "item_type": self.item_type,
            "quantity": self.quantity,
            "weight_per_unit": self.weight_per_unit,
            "cost": self.cost,
            "is_consumable": self.is_consumable,
            "is_cursed": self.is_cursed,
            "description": self.description,
        }
