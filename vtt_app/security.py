"""Security utilities - provides current_user context for Flask-JWT-Extended."""

from functools import wraps
from flask import _app_ctx_stack, has_request_context
from flask_jwt_extended import get_jwt_identity
from vtt_app.models import User


class CurrentUserProxy:
    """Proxy object that retrieves current user from JWT on access."""

    def __getattr__(self, name):
        """Get attribute from current user."""
        user = self._get_user()
        if user is None:
            raise RuntimeError('Working outside of request context without user')
        return getattr(user, name)

    def _get_user(self):
        """Get current user from JWT identity."""
        if not has_request_context():
            return None
        try:
            user_id = get_jwt_identity()
            if user_id:
                return User.query.get(user_id)
        except:
            pass
        return None

    def __bool__(self):
        """Check if user is authenticated."""
        return self._get_user() is not None

    def __repr__(self):
        user = self._get_user()
        return f'<User {user.id if user else "Anonymous"}>'


# Create a proxy instance that acts like current_user
current_user = CurrentUserProxy()
