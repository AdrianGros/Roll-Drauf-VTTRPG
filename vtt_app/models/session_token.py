"""M43: Session token model for character/creature placement on map."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow
import math


class SessionToken(db.Model):
    """Token (character/creature) placed on a map layer in a session (M43).

    Tracks position, visibility, rotation, and rendering properties.
    """

    __tablename__ = 'session_tokens'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    layer_id = db.Column(db.Integer, db.ForeignKey('session_map_layers.id'), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id'), nullable=True, index=True)

    name = db.Column(db.String(100), nullable=False)

    # Position and dimensions
    x = db.Column(db.Integer, nullable=False)  # Pixel position
    y = db.Column(db.Integer, nullable=False)  # Pixel position
    size = db.Column(db.Integer, default=70)  # Pixel size (default 1 grid square)

    # Visual properties
    color = db.Column(db.String(7), default='#FF0000')  # Hex color
    rotation = db.Column(db.Integer, default=0)  # Degrees (0-359)

    # Visibility
    is_visible_to_players = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    session = db.relationship('GameSession', backref='tokens', lazy=True)
    layer = db.relationship('SessionMapLayer', backref='tokens', lazy=True)
    character = db.relationship('Character', backref='session_tokens', lazy=True)

    __table_args__ = (
        db.Index('idx_session_token_location', 'session_id', 'layer_id'),
    )

    def __repr__(self):
        return f'<SessionToken {self.id} {self.name} at ({self.x}, {self.y})>'

    def serialize(self):
        """Return JSON-safe dict."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'layer_id': self.layer_id,
            'character_id': self.character_id,
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'size': self.size,
            'color': self.color,
            'rotation': self.rotation,
            'is_visible_to_players': self.is_visible_to_players,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def move(self, x, y):
        """
        Move token to new position.

        Args:
            x: New X coordinate (pixels)
            y: New Y coordinate (pixels)
        """
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("Coordinates must be numeric")

        self.x = int(x)
        self.y = int(y)
        self.updated_at = utcnow()
        db.session.commit()

    def rotate(self, degrees):
        """
        Rotate token by specified degrees.

        Args:
            degrees: Rotation angle (0-359)

        Raises:
            ValueError: If degrees not in valid range
        """
        if not isinstance(degrees, (int, float)):
            raise ValueError("Rotation must be numeric")

        normalized = int(degrees) % 360
        self.rotation = normalized
        self.updated_at = utcnow()
        db.session.commit()

    def distance_to(self, other_token):
        """
        Calculate Euclidean distance to another token.

        Args:
            other_token: Another SessionToken

        Returns:
            float: Distance in pixels
        """
        dx = self.x - other_token.x
        dy = self.y - other_token.y
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def get_layer_tokens(layer_id):
        """Get all tokens on a specific layer, ordered by creation."""
        return SessionToken.query.filter_by(layer_id=layer_id).order_by(
            SessionToken.created_at
        ).all()

    @staticmethod
    def get_session_tokens(session_id):
        """Get all tokens in a session."""
        return SessionToken.query.filter_by(session_id=session_id).all()
