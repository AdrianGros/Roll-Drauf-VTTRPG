"""
Auth package - authentication routes and utilities.
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from vtt_app.auth.routes import (
    register, login, logout, me, check, refresh,
    mfa_setup, mfa_verify, mfa_disable
)

__all__ = [
    'auth_bp',
    'register', 'login', 'logout', 'me', 'check', 'refresh',
    'mfa_setup', 'mfa_verify', 'mfa_disable'
]
