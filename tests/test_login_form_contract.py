"""Regression contracts for the visible login form states."""

from pathlib import Path


LOGIN_TEMPLATE = Path(__file__).parents[1] / "vtt/templates/login.html"


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
