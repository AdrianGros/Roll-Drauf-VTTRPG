"""Character model for D&D character sheets."""

from datetime import datetime
from vtt_app.extensions import db


class Character(db.Model):
    """D&D Character with stats, abilities, equipment, spells."""

    __tablename__ = 'characters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True)
    
    # Basic Info
    name = db.Column(db.String(100), nullable=False)
    race = db.Column(db.String(50))  # Human, Elf, Dwarf, etc.
    class_name = db.Column(db.String(50))  # Barbarian, Bard, Cleric, etc.
    background = db.Column(db.String(100))
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    
    # Combat Stats
    ac = db.Column(db.Integer, default=10)  # Armor Class
    hp_current = db.Column(db.Integer, default=10)
    hp_max = db.Column(db.Integer, default=10)
    mana_current = db.Column(db.Integer, default=0)
    mana_max = db.Column(db.Integer, default=0)
    
    # Ability Scores (D&D 5e)
    str_score = db.Column(db.Integer, default=10)  # Strength
    dex_score = db.Column(db.Integer, default=10)  # Dexterity
    con_score = db.Column(db.Integer, default=10)  # Constitution
    int_score = db.Column(db.Integer, default=10)  # Intelligence
    wis_score = db.Column(db.Integer, default=10)  # Wisdom
    cha_score = db.Column(db.Integer, default=10)  # Charisma
    
    proficiency_bonus = db.Column(db.Integer, default=2)
    
    # Character Data (JSON blob for flexibility)
    # Contains: skills, proficiencies, traits, ideals, bonds, flaws, etc.
    character_data = db.Column(db.JSON, default=dict)
    
    # Avatar/Token
    token_url = db.Column(db.String(255))  # Path to token image
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)  # Soft delete
    
    # Relationships
    user = db.relationship('User', backref='characters')
    campaign = db.relationship('Campaign', backref='characters')
    spells = db.relationship('Spell', backref='character', cascade='all, delete-orphan')
    equipment = db.relationship('Equipment', backref='character', cascade='all, delete-orphan')
    inventory = db.relationship('InventoryItem', backref='character', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Character {self.name} lvl {self.level}>'
    
    def get_ability_modifier(self, ability_score):
        """Calculate modifier from ability score."""
        return (ability_score - 10) // 2
    
    def get_str_mod(self):
        return self.get_ability_modifier(self.str_score)
    
    def get_dex_mod(self):
        return self.get_ability_modifier(self.dex_score)
    
    def get_con_mod(self):
        return self.get_ability_modifier(self.con_score)
    
    def get_int_mod(self):
        return self.get_ability_modifier(self.int_score)
    
    def get_wis_mod(self):
        return self.get_ability_modifier(self.wis_score)
    
    def get_cha_mod(self):
        return self.get_ability_modifier(self.cha_score)
    
    def is_alive(self):
        """Check if character still has HP."""
        return self.hp_current > 0
    
    def take_damage(self, amount):
        """Apply damage to character."""
        self.hp_current = max(0, self.hp_current - amount)
        db.session.commit()
    
    def heal(self, amount):
        """Heal character."""
        self.hp_current = min(self.hp_max, self.hp_current + amount)
        db.session.commit()
    
    def serialize(self, include_details=False):
        """Return JSON-safe dict."""
        data = {
            'id': self.id,
            'name': self.name,
            'race': self.race,
            'class': self.class_name,
            'level': self.level,
            'hp': f"{self.hp_current}/{self.hp_max}",
            'ac': self.ac,
            'token_url': self.token_url,
            'created_at': self.created_at.isoformat()
        }
        if include_details:
            data.update({
                'str': self.str_score,
                'dex': self.dex_score,
                'con': self.con_score,
                'int': self.int_score,
                'wis': self.wis_score,
                'cha': self.cha_score,
                'xp': self.xp,
                'background': self.background,
                'spells_count': len(self.spells),
                'equipment_count': len(self.equipment),
                'inventory_count': len(self.inventory)
            })
        return data
