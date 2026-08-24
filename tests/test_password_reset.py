"""Password recovery contracts: privacy, single use, and session revocation."""

import re

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import PasswordResetToken, Role, Session, User


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ("Player", "DM", "Admin"):
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "reset_player",
            "email": "reset@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 201


def test_reset_request_is_uniform_for_known_and_unknown_email(client, app, monkeypatch):
    sent = {}

    def capture_mail(*, recipient, reset_url):
        sent.update(recipient=recipient, reset_url=reset_url)

    monkeypatch.setattr("vtt.auth.routes.send_password_reset_email", capture_mail)
    _register(client)

    known = client.post(
        "/api/auth/password-reset/request",
        json={"email": "RESET@example.com"},
    )
    unknown = client.post(
        "/api/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )

    assert known.status_code == unknown.status_code == 202
    assert known.get_json() == unknown.get_json()
    assert sent["recipient"] == "reset@example.com"
    assert re.search(r"token=[A-Za-z0-9_-]+", sent["reset_url"])
    with app.app_context():
        assert PasswordResetToken.query.count() == 1


def test_reset_is_single_use_and_revokes_sessions(client, app, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "vtt.auth.routes.send_password_reset_email",
        lambda *, recipient, reset_url: sent.update(reset_url=reset_url),
    )
    _register(client)

    client.post(
        "/api/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )
    token = sent["reset_url"].split("token=", 1)[1]
    first = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "NewSecurePass123!"},
    )
    second = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "AnotherSecurePass123!"},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    with app.app_context():
        assert Session.query.filter_by(revoked_at=None).count() == 0
        user = User.query.filter_by(email="reset@example.com").one()
        assert user.check_password("NewSecurePass123!")

    login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "NewSecurePass123!"},
    )
    assert login.status_code == 200
