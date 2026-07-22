"""
Flask extensions (singleton instances) for shared use across the application.
"""

import os

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


def _parse_rate_limits(raw_value, fallback):
    if not raw_value:
        return list(fallback)
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=_parse_rate_limits(
        os.getenv("RATELIMIT_DEFAULT_LIMITS"),
        ["200 per day", "50 per hour"],
    ),
)
socketio = SocketIO()
migrate = Migrate()
