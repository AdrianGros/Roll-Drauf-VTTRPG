"""
Configuration for Flask application (dev/test/production).
"""

import os
from datetime import timedelta


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value, default=0):
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_origins(raw_value, fallback):
    if not raw_value:
        return list(fallback)
    return [origin.strip() for origin in str(raw_value).split(",") if origin.strip()]


def _parse_csv(raw_value, fallback):
    if not raw_value:
        return list(fallback)
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


class Config:
    """Base configuration."""

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-prod-immediately')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True
    JWT_ACCESS_COOKIE_PATH = '/'
    JWT_REFRESH_COOKIE_PATH = '/api/auth/refresh'
    JWT_ACCESS_CSRF_COOKIE_PATH = '/'
    JWT_REFRESH_CSRF_COOKIE_PATH = '/api/auth/refresh'
    JWT_SESSION_COOKIE = True

    # CORS
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5000',
        'http://127.0.0.1:5000'
    ]

    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    # Flask-Limiter reads RATELIMIT_STORAGE_URI from app config.
    RATELIMIT_STORAGE_URI = RATELIMIT_STORAGE_URL
    RATELIMIT_SWALLOW_ERRORS = _parse_bool(os.getenv("RATELIMIT_SWALLOW_ERRORS"), default=True)

    # Bcrypt
    BCRYPT_LOG_ROUNDS = 12

    # HTTPS
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = False  # Set True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Community / voice readiness
    VOICE_ENABLED = False
    METRICS_ENABLED = True
    LOG_JSON = _parse_bool(os.getenv("LOG_JSON"), default=True)
    AUTO_CREATE_SCHEMA = True

    # Socket/queue
    REDIS_URL = os.getenv("REDIS_URL")
    SOCKETIO_MESSAGE_QUEUE = os.getenv("SOCKETIO_MESSAGE_QUEUE")

    # Release gate defaults (M14)
    RELEASE_GATE_MIN_UPTIME_SECONDS = 0
    RELEASE_GATE_MIN_REQUESTS = 0
    RELEASE_GATE_MAX_5XX_RATE = 0.05
    RELEASE_GATE_MAX_SLOW_REQUEST_RATE = 0.10
    RELEASE_GATE_MAX_SOCKET_RESYNC_RATE = 0.20
    RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE = 0.30
    RELEASE_GATE_REQUIRE_RUNBOOKS = False
    RELEASE_GATE_REQUIRED_FILES = (
        "ops/runbooks/backup_restore.md",
        "ops/runbooks/failover.md",
        "ops/scripts/backup_db.ps1",
        "ops/scripts/restore_db.ps1",
        "ops/scripts/migrate_db.ps1",
    )


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///vtt.db'
    )
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False
    REDIS_URL = os.getenv("REDIS_URL")
    SOCKETIO_MESSAGE_QUEUE = os.getenv("SOCKETIO_MESSAGE_QUEUE", REDIS_URL)
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_STORAGE_URI = RATELIMIT_STORAGE_URL
    CORS_ORIGINS = _parse_origins(os.getenv("CORS_ORIGINS"), Config.CORS_ORIGINS)
    RELEASE_GATE_MIN_UPTIME_SECONDS = _parse_int(os.getenv("RELEASE_GATE_MIN_UPTIME_SECONDS"), 0)
    RELEASE_GATE_MIN_REQUESTS = _parse_int(os.getenv("RELEASE_GATE_MIN_REQUESTS"), 0)
    RELEASE_GATE_MAX_5XX_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_5XX_RATE"), 0.10)
    RELEASE_GATE_MAX_SLOW_REQUEST_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SLOW_REQUEST_RATE"), 0.20)
    RELEASE_GATE_MAX_SOCKET_RESYNC_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SOCKET_RESYNC_RATE"), 0.30)
    RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE"), 0.40)
    RELEASE_GATE_REQUIRE_RUNBOOKS = _parse_bool(os.getenv("RELEASE_GATE_REQUIRE_RUNBOOKS"), default=False)
    RELEASE_GATE_REQUIRED_FILES = tuple(
        _parse_csv(os.getenv("RELEASE_GATE_REQUIRED_FILES"), Config.RELEASE_GATE_REQUIRED_FILES)
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_SECRET_KEY = "test-secret-key-with-at-least-32-bytes"
    BCRYPT_LOG_ROUNDS = 4  # Faster for tests
    RATELIMIT_ENABLED = False  # Disable rate limiting in tests
    JWT_COOKIE_CSRF_PROTECT = False
    AUTO_CREATE_SCHEMA = True
    METRICS_ENABLED = True
    RELEASE_GATE_MIN_UPTIME_SECONDS = 0
    RELEASE_GATE_MIN_REQUESTS = 0
    RELEASE_GATE_MAX_5XX_RATE = 1.0
    RELEASE_GATE_MAX_SLOW_REQUEST_RATE = 1.0
    RELEASE_GATE_MAX_SOCKET_RESYNC_RATE = 1.0
    RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE = 1.0
    RELEASE_GATE_REQUIRE_RUNBOOKS = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SESSION_COOKIE_SECURE = True
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_COOKIE_SECURE = True
    SECRET_KEY = os.getenv("SECRET_KEY")
    REDIS_URL = os.getenv("REDIS_URL")
    SOCKETIO_MESSAGE_QUEUE = os.getenv("SOCKETIO_MESSAGE_QUEUE", REDIS_URL)
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL")
    RATELIMIT_STORAGE_URI = RATELIMIT_STORAGE_URL
    CORS_ORIGINS = _parse_origins(os.getenv("CORS_ORIGINS"), [])
    AUTO_CREATE_SCHEMA = _parse_bool(os.getenv("AUTO_CREATE_SCHEMA"), default=False)
    VOICE_ENABLED = _parse_bool(os.getenv("VOICE_ENABLED"), default=False)
    METRICS_ENABLED = _parse_bool(os.getenv("METRICS_ENABLED"), default=True)
    RELEASE_GATE_MIN_UPTIME_SECONDS = _parse_int(os.getenv("RELEASE_GATE_MIN_UPTIME_SECONDS"), 300)
    RELEASE_GATE_MIN_REQUESTS = _parse_int(os.getenv("RELEASE_GATE_MIN_REQUESTS"), 200)
    RELEASE_GATE_MAX_5XX_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_5XX_RATE"), 0.01)
    RELEASE_GATE_MAX_SLOW_REQUEST_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SLOW_REQUEST_RATE"), 0.05)
    RELEASE_GATE_MAX_SOCKET_RESYNC_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SOCKET_RESYNC_RATE"), 0.10)
    RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE = _parse_float(os.getenv("RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE"), 0.20)
    RELEASE_GATE_REQUIRE_RUNBOOKS = _parse_bool(os.getenv("RELEASE_GATE_REQUIRE_RUNBOOKS"), default=True)
    RELEASE_GATE_REQUIRED_FILES = tuple(
        _parse_csv(os.getenv("RELEASE_GATE_REQUIRED_FILES"), Config.RELEASE_GATE_REQUIRED_FILES)
    )

    REQUIRED_ENV_VARS = (
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "RATELIMIT_STORAGE_URL",
        "CORS_ORIGINS",
    )


# M17: Platform roles (8-level hierarchy)
PLATFORM_ROLES = {
    'owner': 100,
    'admin': 80,
    'moderator': 60,
    'supporter': 40,
}

# M17: Profile tiers (subscription tiers)
PROFILE_TIERS = {
    'listener': {
        'name': 'Listener',
        'storage_gb': 0.5,
        'active_campaigns': 1,
    },
    'player': {
        'name': 'Player',
        'storage_gb': 1.0,
        'active_campaigns': 3,
    },
    'dm': {
        'name': 'Dungeon Master',
        'storage_gb': 1.0,
        'active_campaigns': 3,
    },
    'headmaster': {
        'name': 'Headmaster',
        'storage_gb': 5.0,
        'active_campaigns': 5,
    },
}

class StagingConfig(DevelopmentConfig):
    """Staging configuration (like development but stricter)."""
    DEBUG = False
    TESTING = False


config_by_name = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
