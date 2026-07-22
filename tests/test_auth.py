"""
Test suite for M3 authentication endpoints.
"""

import pytest
from vtt import create_app
from vtt.extensions import db
from vtt.models import RegistrationKey, Role, User


@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app(config_name='testing')
    
    with app.app_context():
        db.create_all()
        # Create default roles
        for role_name in ['Player', 'DM', 'Admin']:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def _issue_registration_key(
    key_code: str = "SPELL-TEST-ABCD-EFGH",
    *,
    tier: str = "player",
    uses_remaining: int = 1,
):
    key = RegistrationKey(
        key_code=key_code,
        key_name=f"Test key {key_code}",
        key_batch_id=f"test-batch-{key_code}",
        tier=tier,
        max_uses=uses_remaining,
        uses_remaining=uses_remaining,
    )
    db.session.add(key)
    db.session.commit()
    return key


class TestRegister:
    def test_register_success(self, client):
        """Test successful user registration."""
        _issue_registration_key()
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['username'] == 'testuser'

    def test_register_duplicate_username(self, client):
        """Test registration with duplicate username."""
        _issue_registration_key("SPELL-TEST-1111-AAAA")
        _issue_registration_key("SPELL-TEST-2222-BBBB")
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test1@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-TEST-1111-AAAA',
        })
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test2@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-TEST-2222-BBBB',
        })
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        _issue_registration_key()
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'weak',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        assert response.status_code == 400

    def test_register_requires_registration_key(self, client):
        """Test registration requires a valid registration key."""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
        })
        assert response.status_code == 400
        assert response.get_json()['error'] == 'registration key required'


class TestLogin:
    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        _issue_registration_key()
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        
        # Login
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'SecurePass123!'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        set_cookie_values = response.headers.getlist('Set-Cookie')
        assert any('access_token_cookie=' in cookie for cookie in set_cookie_values)
        assert any('refresh_token_cookie=' in cookie for cookie in set_cookie_values)

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post('/api/auth/login', json={
            'username': 'testuser'
        })
        assert response.status_code == 400


class TestMe:
    def test_me_authenticated(self, client):
        """Test /me endpoint with valid cookie-based auth."""
        # Register and login
        _issue_registration_key()
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'SecurePass123!'
        })

        # Get user info
        response = client.get('/api/auth/me')
        assert response.status_code == 200
        data = response.get_json()
        assert data['username'] == 'testuser'

    def test_me_unauthenticated(self, client):
        """Test /me endpoint without token."""
        response = client.get('/api/auth/me')
        assert response.status_code == 401


class TestPasswordValidation:
    def test_password_length(self, client):
        """Test password length validation."""
        _issue_registration_key()
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Short1!',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        assert response.status_code == 400

    def test_password_complexity(self, client):
        """Test password complexity requirements."""
        # Missing special char
        _issue_registration_key()
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'NoSpecial123',
            'registration_key': 'SPELL-TEST-ABCD-EFGH',
        })
        assert response.status_code == 400


class TestCsrfProtection:
    def _register_and_login(self, client):
        _issue_registration_key("SPELL-CSRF-ABCD-EFGH")
        client.post('/api/auth/register', json={
            'username': 'csrf_user',
            'email': 'csrf@example.com',
            'password': 'SecurePass123!',
            'registration_key': 'SPELL-CSRF-ABCD-EFGH',
        })
        response = client.post('/api/auth/login', json={
            'username': 'csrf_user',
            'password': 'SecurePass123!'
        })
        assert response.status_code == 200

    def test_post_requires_csrf_when_enabled(self, client):
        """Mutating endpoints reject requests without CSRF token when enabled."""
        client.application.config['JWT_COOKIE_CSRF_PROTECT'] = True
        self._register_and_login(client)

        response = client.post('/api/auth/mfa/setup')
        assert response.status_code == 401
        data = response.get_json() or {}
        assert 'csrf' in data.get('error', '').lower()

    def test_post_accepts_csrf_when_enabled(self, client):
        """Mutating endpoints accept requests with CSRF token when enabled."""
        client.application.config['JWT_COOKIE_CSRF_PROTECT'] = True
        self._register_and_login(client)

        csrf_cookie = client.get_cookie('csrf_access_token')
        assert csrf_cookie is not None

        response = client.post('/api/auth/mfa/setup', headers={
            'X-CSRF-TOKEN': csrf_cookie.value
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'provisioning_uri' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
