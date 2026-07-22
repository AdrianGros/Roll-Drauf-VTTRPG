"""Character model for character sheets and archive continuity."""

from datetime import datetime
from vtt.extensions import db


class Character(db.Model):
    """Character with stats, abilities, equipment, spells, and identity media."""

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
    avatar_url = db.Column(db.String(255))  # Path to avatar image
    token_url = db.Column(db.String(255))  # Path to token image
    avatar_storage_key = db.Column(db.String(512))
    avatar_mime_type = db.Column(db.String(100))
    token_storage_key = db.Column(db.String(512))
    token_mime_type = db.Column(db.String(100))
    
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
        avatar_url = self.avatar_url or (
            f'/api/characters/{self.id}/identity/avatar' if self.avatar_storage_key else None
        )
        token_url = self.token_url or (
            f'/api/characters/{self.id}/identity/token' if self.token_storage_key else None
        )
        character_data = self.character_data if isinstance(self.character_data, dict) else {}
        roll_drauf_light = character_data.get('roll_drauf_light') if isinstance(character_data.get('roll_drauf_light'), dict) else {}
        species = roll_drauf_light.get('species', {}) if isinstance(roll_drauf_light.get('species'), dict) else {}
        faction = roll_drauf_light.get('faction', {}) if isinstance(roll_drauf_light.get('faction'), dict) else {}
        class_data = roll_drauf_light.get('class', {}) if isinstance(roll_drauf_light.get('class'), dict) else {}
        background = roll_drauf_light.get('background', {}) if isinstance(roll_drauf_light.get('background'), dict) else {}
        species_name = species.get('name') or self.race
        class_name = class_data.get('name') or self.class_name
        background_name = background.get('name') or self.background
        content = roll_drauf_light.get('content') if isinstance(roll_drauf_light.get('content'), dict) else {}
        progression = roll_drauf_light.get('progression') if isinstance(roll_drauf_light.get('progression'), dict) else {}
        data = {
            'id': self.id,
            'name': self.name,
            'race': species_name,
            'species': species_name,
            'species_slug': species.get('slug'),
            'faction': faction.get('name'),
            'faction_slug': faction.get('slug'),
            'class': class_name,
            'class_slug': class_data.get('slug'),
            'background': background_name,
            'background_slug': background.get('slug'),
            'system_id': roll_drauf_light.get('system_id'),
            'campaign_id': self.campaign_id,
            'level': self.level,
            'hp': f"{self.hp_current}/{self.hp_max}",
            'ac': self.ac,
            'avatar_url': avatar_url,
            'token_url': token_url,
            'created_at': self.created_at.isoformat(),
            # M24: progression + content summary
            'training_bonus': content.get('training_bonus'),
            'progression_level': progression.get('current_level'),
            'progression_level_cap': progression.get('level_cap'),
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
                'background': background_name,
                'spells_count': len(self.spells),
                'equipment_count': len(self.equipment),
                'inventory_count': len(self.inventory),
                # M24: full progression + content blocks for sheet/export
                'progression': progression or None,
                'content': content or None,
            })
        return data
