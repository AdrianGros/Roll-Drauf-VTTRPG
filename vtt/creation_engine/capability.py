"""Who may open the Creation Engine. Import-light: the dashboard reads this on every page load."""

from flask import current_app


def account_usable(user):
    return bool(user is not None and user.is_active and not user.is_suspended
                and user.account_state in (None, "active"))


def authoring_available(user):
    """Display capability for the Creation Engine entry points (creation-engine-nav.js)."""
    return bool(current_app.config.get("CE_AUTHORING")) and account_usable(user)
