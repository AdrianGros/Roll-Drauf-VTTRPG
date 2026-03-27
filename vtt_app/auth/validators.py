"""
Validators for user input (password, email, username).
"""

import re
from email_validator import validate_email, EmailNotValidError


COMMON_PASSWORDS = {
    'password', 'password123', '123456', 'qwerty', 'abc123', 'letmein',
    '12345678', '123456789', '1234567890', 'admin', 'admin123', 'root'
}

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def validate_password(password: str, username: str = '', email: str = '') -> tuple[bool, str]:
    """
    Validate password against security rules.
    Returns (is_valid, error_message).
    """

    if not password:
        return False, "Password is required"

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"

    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f"Password must be at most {PASSWORD_MAX_LENGTH} characters"

    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common. Choose a stronger password"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*_\-+=]', password):
        return False, "Password must contain at least one special character (!@#$%^&*_-+=)"

    if username and password.lower() == username.lower():
        return False, "Password cannot be the same as username"

    if email and password.lower() == email.lower():
        return False, "Password cannot be the same as email"

    return True, ""


def validate_email_address(email: str) -> tuple[bool, str]:
    """
    Validate email format.
    Returns (is_valid, error_message).
    """

    if not email:
        return False, "Email is required"

    try:
        validate_email(email, check_deliverability=False)
        return True, ""
    except EmailNotValidError as e:
        return False, f"Invalid email: {str(e)}"


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate username format.
    Returns (is_valid, error_message).
    """

    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be at most 50 characters"

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, ""
