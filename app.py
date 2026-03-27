"""
Entry point for roll drauf vtt application.
"""

import os
from dotenv import load_dotenv
from vtt_app import create_app
from vtt_app.extensions import socketio, db
from vtt_app.models import Role


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# Load environment variables
load_dotenv()

# Create Flask app
app = create_app(config_name=os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    """Add objects to shell context."""
    return {'db': db}

def _ensure_default_roles():
    """Initialize default roles once at startup, not per request."""
    with app.app_context():
        if not Role.query.first():
            from vtt_app.models.role import init_default_roles
            init_default_roles(db.session)


_ensure_default_roles()

if __name__ == '__main__':
    env_name = os.getenv('FLASK_ENV', 'development')
    if env_name == 'production':
        raise RuntimeError(
            "Direct production start via app.py is disabled. "
            "Use a production WSGI/ASGI server (see QUICKSTART/README)."
        )

    debug_mode = _parse_bool(os.getenv('FLASK_DEBUG'), default=False)
    socketio.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        debug=debug_mode,
        allow_unsafe_werkzeug=debug_mode
    )
