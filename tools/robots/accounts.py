"""Minting the one thing a robot cannot get through the real UI.

VTT's registration form is real and self-contained (no Discord round-trip
needed when DISCORD_LOGIN_ENABLED=false, which the disposable stack
always sets -- see stack.py). The single piece a robot cannot obtain by
clicking around is a registration key: in real life a DM hands one out
by hand outside the app. Minting a batch is an operator action (the same
`create_registration_keys` function app.py's `flask bootstrap-admin` CLI
command calls, per vtt/endpoints/registration_keys.py's own docstring:
"Shared core used by both the admin HTTP endpoint and CLI bootstrap
tooling") -- not a test-only backdoor.

Everything after the key exists -- filling the register form, logging
in, creating campaigns, rolling dice -- happens through the real browser
UI in session.py/flows.py, exactly as a player would.
"""

from __future__ import annotations

import os
import secrets


def mint_registration_keys(database_url: str, *, count: int,
                           tier: str = "dm") -> list[str]:
    """Push an app context against the disposable database and mint a
    batch of registration keys the same way `flask bootstrap-admin`
    does (app.py's own CLI command) -- including the operator account
    log_audit needs: create_registration_keys writes a 'key_batch_generated'
    audit row and requires a resolvable performer (vtt/utils/audit.py
    falls back to Flask-Login's current_user, which does not exist
    outside a real request context -- calling it with no performed_by
    from a script raises "Audit performer could not be resolved", not a
    product bug, just this function's own omission if it forgets one).

    Also ensures the schema exists and default roles are seeded --
    normally AUTO_CREATE_SCHEMA does this on the app's first request, but
    minting keys happens BEFORE the app process is even started, so it
    is done explicitly here against the same database.
    """
    os.environ["DATABASE_URL"] = database_url
    from vtt import create_app
    from vtt.extensions import db
    from vtt.endpoints.registration_keys import create_registration_keys
    from vtt.models import Role, User

    app = create_app(config_name="development")
    with app.app_context():
        db.create_all()
        if not Role.query.first():
            from vtt.models.role import init_default_roles
            init_default_roles(db.session)
            db.session.commit()

        operator = User.query.filter_by(username="robots-operator").first()
        if operator is None:
            admin_role = (Role.query.filter_by(name="Admin").first()
                         or Role.query.first())
            operator = User(
                username="robots-operator",
                email="robots-operator@robots.roll-drauf.de",
                role_id=admin_role.id,
                platform_role="owner",
                profile_tier="headmaster",
                is_active=True,
                email_verified=True,
                account_state="active",
            )
            operator.set_password(secrets.token_urlsafe(24))
            db.session.add(operator)
            db.session.commit()

        batch = create_registration_keys(
            count=count, tier=tier, batch_name="robots",
            performed_by=operator)
        return list(batch["keys"])
