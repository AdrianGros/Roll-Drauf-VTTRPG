"""
Auth package - authentication routes and utilities.
"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from vtt.auth.routes import (
    register, login, logout, me, check, refresh,
    mfa_setup, mfa_verify, mfa_disable,
    request_password_reset, confirm_password_reset, change_password,
)

__all__ = [
    'auth_bp',
    'register', 'login', 'logout', 'me', 'check', 'refresh',
    'mfa_setup', 'mfa_verify', 'mfa_disable',
    'request_password_reset', 'confirm_password_reset', 'change_password'
]
