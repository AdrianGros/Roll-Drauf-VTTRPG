"""Regression contracts for the visible login form states."""

import hashlib
from pathlib import Path


LOGIN_TEMPLATE = Path(__file__).parents[1] / "vtt/templates/login.html"
PROFILE_BUNNY_ASSET = Path(__file__).parents[1] / "vtt/static/assets/sternenstaub/illustrations/profile-bunny.png"


def test_empty_password_error_surface_is_not_rendered_as_a_bar():
    html = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert ".book-auth-error:empty" in html
    assert ".book-auth-error:empty {\n            display: none;\n        }" in html


def test_login_actions_are_compact_buttons_without_redundant_prompt():
    html = LOGIN_TEMPLATE.read_text(encoding="utf-8")
    action_block = html.split('<div class="book-auth-actions">', 1)[1].split('</div>', 1)[0]

    assert 'id="passwordLoginSubmitBtn"' in action_block
    assert 'class="btn btn-primary book-auth-action" href="/signup.html">Registrieren</a>' in action_block
    assert 'class="btn btn-primary book-auth-action" href="/forgot-password.html">Passwort vergessen</a>' in action_block
    assert action_block.count('class="btn') == 3
    assert "Noch kein Konto?" not in action_block
    assert "Jetzt registrieren" not in action_block
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in html


def test_discord_login_button_keeps_blue_theme_after_shared_button_css():
    html = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert "#login-content .book-login-btn" in html
    assert "background: #5865f2;" in html
    assert "margin: 24px 0 12px;" in html


def test_login_profile_art_uses_the_exact_discord_attachment():
    html = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert PROFILE_BUNNY_ASSET.is_file()
    assert hashlib.sha256(PROFILE_BUNNY_ASSET.read_bytes()).hexdigest() == (
        "bb07de4949c0d05c39cafcd87988fa5784c35dbfe78fa874ebf9bda3062e9697"
    )
    assert '<div class="login-profile-art" aria-hidden="true">' in html
    assert '<img src="/static/assets/sternenstaub/illustrations/profile-bunny.png" alt="">' in html
    assert "object-fit: contain;" in html
