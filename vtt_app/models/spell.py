"""Spell model for character spellcasting."""

from datetime import datetime
from vtt_app.extensions import db


class Spell(db.Model):
    """Spell that a character can cast."""

    __tablename__ = 'spells'

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=False, index=True)

    # Spell Info
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, default=0)  # 0 = cantrip, 1-9 = spell levels
    school = db.Column(db.String(50))  # Abjuration, Conjuration, Divination, etc.

    # Mechanics
    casting_time = db.Column(db.String(50))  # "1 action", "1 bonus action", etc.
    duration = db.Column(db.String(100))  # "Instant", "Concentration, up to 1 minute", etc.
    range_distance = db.Column(db.String(50))  # "Self", "60 feet", "Sight", etc.

    # Spell Slots (for prepared casters)
    is_prepared = db.Column(db.Boolean, default=True)
    is_ritual = db.Column(db.Boolean, default=False)

    # Description and rules
    description = db.Column(db.Text)  # Full spell text

    # Damage and effects (JSON for flexibility)
    damage_dice = db.Column(db.String(20))  # "2d6", "3d8", etc.
    damage_type = db.Column(db.String(50))  # Fire, Cold, Necrotic, etc.

    custom_data = db.Column(db.JSON, default=dict)  # Custom fields

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Spell {self.name} (Level {self.level})>'

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'school': self.school,
            'casting_time': self.casting_time,
            'range': self.range_distance,
            'duration': self.duration,
            'is_prepared': self.is_prepared,
            'is_ritual': self.is_ritual,
            'damage_dice': self.damage_dice,
            'damage_type': self.damage_type
        }
