"""Equipment model for character gear."""

from datetime import datetime
from vtt_app.extensions import db


class Equipment(db.Model):
    """Equipment/Armor that a character can equip."""

    __tablename__ = 'equipment'

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False, index=True)

    # Basic Info
    name = db.Column(db.String(100), nullable=False)
    equipment_type = db.Column(db.String(50))  # Weapon, Armor, Shield, Accessory
    rarity = db.Column(db.String(50))  # Common, Uncommon, Rare, Very Rare, Legendary

    # Combat Stats
    ac_bonus = db.Column(db.Integer, default=0)  # Armor Class bonus
    damage_dice = db.Column(db.String(20))  # Weapon damage (e.g., "1d8", "2d6")
    damage_type = db.Column(db.String(50))  # Slashing, Piercing, Bludgeoning, Magical

    # Properties
    is_equipped = db.Column(db.Boolean, default=False)
    is_cursed = db.Column(db.Boolean, default=False)

    # Details
    weight = db.Column(db.Float)  # in lbs
    cost = db.Column(db.String(50))  # e.g., "50 gp"
    description = db.Column(db.Text)

    # Special abilities/properties
    special_properties = db.Column(db.JSON, default=dict)  # e.g., {"magical": True, "bonus": 1}

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Equipment {self.name}>'

    def equip(self):
        """Mark equipment as equipped."""
        self.is_equipped = True
        db.session.commit()

    def unequip(self):
        """Mark equipment as unequipped."""
        self.is_equipped = False
        db.session.commit()

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.equipment_type,
            'rarity': self.rarity,
            'ac_bonus': self.ac_bonus,
            'damage_dice': self.damage_dice,
            'damage_type': self.damage_type,
            'is_equipped': self.is_equipped,
            'weight': self.weight,
            'cost': self.cost
        }
