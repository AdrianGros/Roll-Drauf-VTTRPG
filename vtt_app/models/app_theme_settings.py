"""
AppThemeSettings model for spellbook theme customization.
"""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class AppThemeSettings(db.Model):
    """Theme configuration for the application spellbook interface."""

    __tablename__ = 'app_theme_settings'

    id = db.Column(db.Integer, primary_key=True)

    # Theme identity
    theme_name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)

    # Color scheme
    primary_color = db.Column(db.String(7), nullable=False, default='#4a235a')  # deep purple
    accent_color = db.Column(db.String(7), nullable=False, default='#d4af37')   # gold
    text_color = db.Column(db.String(7), nullable=False, default='#2a2a2a')     # dark text
    background_color = db.Column(db.String(7), nullable=False, default='#f5e6d3')  # parchment

    # Typography
    font_heading = db.Column(db.String(100), nullable=False, default="'Georgia', serif")
    font_body = db.Column(db.String(100), nullable=False, default="'Segoe UI', sans-serif")

    # Animation settings
    book_animation_speed = db.Column(db.Float, nullable=False, default=2.5)  # seconds

    # Registration key prefix
    key_code_prefix = db.Column(db.String(10), nullable=False, default='SPELL')

    # Status
    is_active = db.Column(db.Boolean, default=False, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def apply(self):
        """Mark this theme as active and deactivate others."""
        # Deactivate all other themes
        AppThemeSettings.query.filter(AppThemeSettings.id != self.id).update({'is_active': False})
        # Activate this theme
        self.is_active = True
        db.session.commit()

    def get_css_variables(self):
        """Return CSS variable definitions for this theme."""
        return {
            '--vtt-primary': self.primary_color,
            '--vtt-accent': self.accent_color,
            '--vtt-text': self.text_color,
            '--vtt-bg': self.background_color,
            '--vtt-dark-bg': '#1a1a1a',
            '--vtt-shadow': 'rgba(0,0,0,0.3)',
            '--vtt-border': self.accent_color,
            '--vtt-font-heading': self.font_heading,
            '--vtt-font-body': self.font_body,
            '--vtt-book-animation-speed': f'{self.book_animation_speed}s',
        }

    def serialize(self):
        """Serialize theme to dict for API responses."""
        return {
            'id': self.id,
            'theme_name': self.theme_name,
            'description': self.description,
            'primary_color': self.primary_color,
            'accent_color': self.accent_color,
            'text_color': self.text_color,
            'background_color': self.background_color,
            'font_heading': self.font_heading,
            'font_body': self.font_body,
            'book_animation_speed': self.book_animation_speed,
            'key_code_prefix': self.key_code_prefix,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_default_theme(cls):
        """Get or create the default spellbook theme."""
        theme = cls.query.filter_by(theme_name='Default Spellbook').first()
        if not theme:
            theme = cls(
                theme_name='Default Spellbook',
                description='Default spellbook theme with deep purple and gold',
                primary_color='#4a235a',
                accent_color='#d4af37',
                text_color='#2a2a2a',
                background_color='#f5e6d3',
                font_heading="'Georgia', serif",
                font_body="'Segoe UI', sans-serif",
                book_animation_speed=2.5,
                key_code_prefix='SPELL',
                is_active=True
            )
            db.session.add(theme)
            db.session.commit()
        return theme

    @classmethod
    def get_active_theme(cls):
        """Get the currently active theme."""
        theme = cls.query.filter_by(is_active=True).first()
        return theme or cls.get_default_theme()

    def __repr__(self):
        return f'<AppThemeSettings {self.theme_name}>'
