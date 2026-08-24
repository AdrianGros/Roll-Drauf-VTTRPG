"""Regression contracts for the visible login form states."""

from pathlib import Path


LOGIN_TEMPLATE = Path(__file__).parents[1] / "vtt/templates/login.html"


def test_empty_password_error_surface_is_not_rendered_as_a_bar():
    html = LOGIN_TEMPLATE.read_text(encoding="utf-8")

    assert ".book-auth-error:empty" in html
    assert ".book-auth-error:empty {\n            display: none;\n        }" in html
