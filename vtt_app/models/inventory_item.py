"""Inventory Item model for character carrying capacity."""

from datetime import datetime
from vtt_app.extensions import db


class InventoryItem(db.Model):
    """Item in character inventory."""

    __tablename__ = 'inventory_items'

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False, index=True)

    # Basic Info
    name = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(50))  # Potion, Scroll, Key, Gem, Consumable, Misc

    # Quantity and Weight
    quantity = db.Column(db.Integer, default=1)
    weight_per_unit = db.Column(db.Float)  # in lbs

    # Value
    cost = db.Column(db.String(50))  # e.g., "50 gp", "2 pp 5 gp"

    # Properties
    is_consumable = db.Column(db.Boolean, default=False)
    is_cursed = db.Column(db.Boolean, default=False)

    # Description and effects
    description = db.Column(db.Text)
    effects = db.Column(db.JSON, default=dict)  # e.g., {"healing": 2, "duration": "10 minutes"}

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<InventoryItem {self.name} x{self.quantity}>'

    def total_weight(self):
        """Calculate total weight of stacked items."""
        if self.weight_per_unit:
            return self.weight_per_unit * self.quantity
        return 0

    def use(self, amount=1):
        """Consume item(s) from inventory."""
        self.quantity -= amount
        if self.quantity <= 0:
            db.session.delete(self)
        db.session.commit()

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.item_type,
            'quantity': self.quantity,
            'weight_per_unit': self.weight_per_unit,
            'total_weight': self.total_weight(),
            'cost': self.cost,
            'is_consumable': self.is_consumable,
            'description': self.description
        }
