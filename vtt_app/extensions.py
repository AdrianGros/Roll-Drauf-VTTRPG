"""
Flask extensions (singleton instances) for shared use across the application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
try:
    from flask_migrate import Migrate
except Exception:  # pragma: no cover - optional dependency guard
    class Migrate:  # type: ignore[override]
        """Fallback no-op migrate extension when Flask-Migrate is unavailable."""

        def init_app(self, _app, _db):
            return None

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
socketio = SocketIO()
migrate = Migrate()
