"""
Entry point for roll drauf vtt application.
"""

import os
import secrets

import click
from dotenv import load_dotenv
from vtt import create_app
from vtt.extensions import socketio, db
from vtt.models import Role


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
            from vtt.models.role import init_default_roles
            init_default_roles(db.session)


_ensure_default_roles()


@app.cli.command('bootstrap-admin')
@click.option('--username', default='admin', help='Username for the local owner account.')
@click.option('--email', default='admin@roll-drauf.local', help='Email for the local owner account.')
@click.option('--password', default=None, help='Password for the owner account (random if omitted).')
@click.option('--key-count', default=5, type=int, help='Number of DM-tier registration keys to mint.')
def bootstrap_admin(username, email, password, key_count):
    """Create a local owner account plus DM registration keys (no Discord required)."""
    from vtt.models import User
    from vtt.endpoints.registration_keys import create_registration_keys

    with app.app_context():
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            click.echo(f"User '{username}' already exists — skipping account creation.")
            user = existing_user
        else:
            admin_role = Role.query.filter_by(name='Admin').first()
            generated_password = password or secrets.token_urlsafe(12)
            user = User(
                username=username,
                email=email,
                role_id=admin_role.id,
                platform_role='owner',
                profile_tier='headmaster',
                is_active=True,
                email_verified=True,
                account_state='active',
            )
            user.set_password(generated_password)
            db.session.add(user)
            db.session.commit()
            click.echo(f"Created owner account -> username: {username}  password: {generated_password}")

        batch = create_registration_keys(count=key_count, tier='dm', batch_name='bootstrap-dm-keys', performed_by=user)
        click.echo(f"Generated {len(batch['keys'])} DM registration keys (tier=dm):")
        for key_code in batch['keys']:
            click.echo(f"  {key_code}")


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
