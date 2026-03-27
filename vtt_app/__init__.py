"""
roll drauf vtt - A D&D Virtual Tabletop for Discord Sessions
App Factory for modular Flask application with Socket.IO, JWT Auth, and Database persistence.
"""

import logging
import os
import time
import uuid
from flask import Flask, g, request
from flask_cors import CORS
from vtt_app.extensions import db, jwt, limiter, migrate, socketio
from vtt_app.config import config_by_name
from vtt_app.utils.time import utcnow


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class _JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field_name in ("request_id", "method", "path", "route", "status_code", "duration_ms", "user_id"):
            field_value = getattr(record, field_name, None)
            if field_value is not None:
                payload[field_name] = field_value
        return str(payload).replace("'", '"')


def _configure_logging(app: Flask):
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        if app.config.get("LOG_JSON", True):
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root_logger.addHandler(handler)


def _validate_production_config(app: Flask):
    if app.config.get("TESTING"):
        return
    if not str(app.config.get("ENV", "")).lower().startswith("prod") and app.config.get("DEBUG", False):
        return

    required = tuple(app.config.get("REQUIRED_ENV_VARS", ()))
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required production env vars: {', '.join(missing)}")

    if app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite"):
        raise RuntimeError("Production database must not be SQLite.")

    insecure_secret_defaults = {
        "SECRET_KEY": "dev-secret-change-in-prod",
        "JWT_SECRET_KEY": "dev-secret-change-in-prod-immediately",
    }
    for key, bad_value in insecure_secret_defaults.items():
        if app.config.get(key) == bad_value:
            raise RuntimeError(f"Unsafe default detected for {key}.")


def _setup_ops_metrics(app: Flask):
    app.extensions["ops_started_at"] = utcnow()
    app.extensions["ops_metrics"] = {
        "requests_total": 0,
        "by_status": {},
        "by_path": {},
        "by_route": {},
        "latency_buckets_ms": {
            "le_10": 0,
            "le_50": 0,
            "le_100": 0,
            "le_250": 0,
            "le_500": 0,
            "gt_500": 0,
        },
        "socket_events_total": 0,
        "socket_events_by_name": {},
        "socket_conflicts_total": 0,
        "socket_resync_requests_total": 0,
        "socket_reconnect_recoveries_total": 0,
        "play_transitions_total": 0,
        "play_transitions_by_target": {},
    }

    @app.before_request
    def _attach_request_context():
        g.request_started = time.perf_counter()
        incoming = request.headers.get("X-Request-ID")
        g.request_id = str(incoming).strip() if incoming else str(uuid.uuid4())

    def _latency_bucket(duration_ms: float) -> str:
        if duration_ms <= 10:
            return "le_10"
        if duration_ms <= 50:
            return "le_50"
        if duration_ms <= 100:
            return "le_100"
        if duration_ms <= 250:
            return "le_250"
        if duration_ms <= 500:
            return "le_500"
        return "gt_500"

    @app.after_request
    def _collect_metrics(response):
        store = app.extensions.get("ops_metrics")
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        response.headers["X-Request-ID"] = request_id
        if not store:
            return response

        duration_ms = 0.0
        started = getattr(g, "request_started", None)
        if started is not None:
            duration_ms = (time.perf_counter() - started) * 1000.0

        path = request.path
        route = request.url_rule.rule if request.url_rule else path
        status = str(response.status_code)
        store["requests_total"] += 1
        store["by_status"][status] = int(store["by_status"].get(status, 0)) + 1
        store["by_path"][path] = int(store["by_path"].get(path, 0)) + 1
        store["by_route"][route] = int(store["by_route"].get(route, 0)) + 1
        bucket = _latency_bucket(duration_ms)
        latency = store.get("latency_buckets_ms", {})
        latency[bucket] = int(latency.get(bucket, 0)) + 1

        logging.getLogger("http.request").info(
            "request complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "route": route,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response


def create_app(config_name=None):
    """Create and configure Flask application."""

    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    app.config["ENV"] = config_name

    _configure_logging(app)
    if config_name == "production":
        _validate_production_config(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins=app.config['CORS_ORIGINS'],
        message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE") or None,
    )

    # CORS configuration
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
        supports_credentials=True,
    )

    # M34: Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if not app.config.get("DEBUG"):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'"
        return response

    _setup_ops_metrics(app)

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload):
        from vtt_app.models import Session
        token_jti = jwt_payload.get("jti")
        if not token_jti:
            return False
        session = Session.query.filter_by(token_jti=token_jti).first()
        return bool(session and session.revoked_at is not None)

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return {"error": reason}, 401

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return {"error": reason}, 401

    @jwt.expired_token_loader
    def handle_expired_token(_jwt_header, _jwt_payload):
        return {"error": "token expired"}, 401

    @jwt.revoked_token_loader
    def handle_revoked_token(_jwt_header, _jwt_payload):
        return {"error": "token revoked"}, 401

    # Register blueprints
    from vtt_app.auth import auth_bp
    from vtt_app.campaigns import campaigns_bp
    from vtt_app.characters import characters_bp
    from vtt_app.community import community_bp
    from vtt_app.ops import ops_bp
    from vtt_app.play import play_bp
    from vtt_app.endpoints.assets import assets_bp
    from vtt_app.endpoints.admin_dashboard import admin_dashboard_bp
    from vtt_app.endpoints.profile_m18 import profile_m18_bp, admin_m18_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(campaigns_bp, url_prefix='/api')
    app.register_blueprint(characters_bp, url_prefix='/api')
    app.register_blueprint(community_bp, url_prefix='/api')
    app.register_blueprint(play_bp, url_prefix='/api/play')
    app.register_blueprint(ops_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(profile_m18_bp)
    app.register_blueprint(admin_m18_bp)

    # Create database tables
    if app.config.get("AUTO_CREATE_SCHEMA", False):
        with app.app_context():
            db.create_all()

    # Socket.IO event handlers
    from vtt_app.socket_handlers import register_socket_handlers
    register_socket_handlers(socketio)

    # REST endpoints for static files
    @app.route('/')
    def index():
        from flask import redirect
        return redirect('/login.html')

    @app.route('/<path:path>')
    def serve_static(path):
        import os
        from flask import jsonify, send_from_directory

        # Try to serve static files
        if path.startswith('static/'):
            return send_from_directory(os.path.abspath('.'), path)

        # Keep API routes JSON-only if no endpoint matched.
        if path.startswith('api/'):
            return jsonify({'error': 'not found'}), 404

        # Try to serve HTML templates
        if path.endswith('.html'):
            template_path = os.path.join(os.path.dirname(__file__), 'templates', path)
            if os.path.exists(template_path):
                return send_from_directory(os.path.join(os.path.dirname(__file__), 'templates'), path)

        # Support extensionless page routes like /dashboard
        template_filename = f'{path}.html'
        template_path = os.path.join(os.path.dirname(__file__), 'templates', template_filename)
        if os.path.exists(template_path):
            return send_from_directory(os.path.join(os.path.dirname(__file__), 'templates'), template_filename)

        # Default: serve login.html for root and unknown paths
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'login.html')
        if os.path.exists(template_path):
            return send_from_directory(os.path.join(os.path.dirname(__file__), 'templates'), 'login.html')

    return app
