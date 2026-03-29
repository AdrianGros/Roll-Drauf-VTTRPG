"""M42: Session map layer model for layered map rendering."""

from vtt_app.extensions import db
from vtt_app.utils.time import utcnow


class SessionMapLayer(db.Model):
    """Map layer within a game session (M42).

    Supports multiple layered maps with visibility, fog of war, and ordering.
    Max 10 layers per session.
    """

    __tablename__ = 'session_map_layers'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.id'), nullable=False, index=True)
    layer_name = db.Column(db.String(100), nullable=False)
    layer_order = db.Column(db.Integer, nullable=False)  # 0-based, must be contiguous

    # Map asset reference (M44)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True, index=True)

    # Map dimensions and grid
    width = db.Column(db.Integer, nullable=False)  # Pixels
    height = db.Column(db.Integer, nullable=False)  # Pixels
    grid_size = db.Column(db.Integer, default=70)  # Pixels per grid square

    # Visibility and effects
    is_visible = db.Column(db.Boolean, default=True)
    fog_of_war_enabled = db.Column(db.Boolean, default=False)
    fog_of_war_data = db.Column(db.JSON)  # Fog of war mask/revealed areas

    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    session = db.relationship('GameSession', backref='map_layers', lazy=True)
    asset = db.relationship('Asset', backref='session_layers', lazy=True)

    __table_args__ = (
        db.Index('idx_session_map_layer', 'session_id', 'layer_order'),
    )

    def __repr__(self):
        return f'<SessionMapLayer {self.id} session={self.session_id} order={self.layer_order}>'

    def serialize(self):
        """Return JSON-safe dict."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'layer_name': self.layer_name,
            'layer_order': self.layer_order,
            'asset_id': self.asset_id,
            'width': self.width,
            'height': self.height,
            'grid_size': self.grid_size,
            'is_visible': self.is_visible,
            'fog_of_war_enabled': self.fog_of_war_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def move_layer(self, new_order):
        """
        Move layer to new position in stack.

        Automatically reorders other layers to maintain contiguity.

        Args:
            new_order: Target layer order (0-based)

        Raises:
            ValueError: If new_order is invalid
        """
        if not isinstance(new_order, int) or new_order < 0:
            raise ValueError("Layer order must be non-negative integer")

        old_order = self.layer_order
        if new_order == old_order:
            return

        # Get all layers in session
        all_layers = SessionMapLayer.query.filter_by(session_id=self.session_id).order_by(
            SessionMapLayer.layer_order
        ).all()

        if new_order >= len(all_layers):
            raise ValueError(f"Layer order {new_order} out of range (max: {len(all_layers)-1})")

        # Reorder
        self.layer_order = new_order
        if new_order < old_order:
            # Moving up (lower order): shift others down
            for layer in all_layers:
                if layer.id != self.id and new_order <= layer.layer_order < old_order:
                    layer.layer_order += 1
        else:
            # Moving down (higher order): shift others up
            for layer in all_layers:
                if layer.id != self.id and old_order < layer.layer_order <= new_order:
                    layer.layer_order -= 1

        db.session.commit()

    @staticmethod
    def get_session_layers(session_id):
        """Get all layers for a session, ordered by layer_order."""
        return SessionMapLayer.query.filter_by(session_id=session_id).order_by(
            SessionMapLayer.layer_order
        ).all()

    @staticmethod
    def validate_layer_order(session_id):
        """
        Validate that layer orders are contiguous (0, 1, 2, ...).

        Returns:
            (is_valid: bool, errors: list[str])
        """
        layers = SessionMapLayer.get_session_layers(session_id)
        errors = []

        # Check contiguity
        for i, layer in enumerate(layers):
            if layer.layer_order != i:
                errors.append(f"Layer {layer.id} has order {layer.layer_order}, expected {i}")

        return len(errors) == 0, errors

    @staticmethod
    def check_layer_limit(session_id):
        """Check if session has reached max layer limit (10)."""
        count = SessionMapLayer.query.filter_by(session_id=session_id).count()
        return count < 10, count
