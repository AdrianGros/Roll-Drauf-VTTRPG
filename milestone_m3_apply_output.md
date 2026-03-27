# M3 Apply Output: Auth & User-Management Design

```
artifact: apply-output
milestone: M3
phase: APPLY
status: complete
date: 2026-03-26
```

---

## Input Summary

- **Discover Output**: milestone_m3_discover_output.md (alle Requirements, Risks, Questions)
- **Current Code**: app.py mit Fragment-Code (JWT refs, pyotp imports, incomplete models)
- **Tech Stack Decision**: Flask + SQLAlchemy + PostgreSQL (SQLite für MVP) + Bcrypt + JWT-Extended + pyotp

---

## Solution Design

### Architecture Overview

**Component Structure** (Folder organization):
```
vtt_app/
├── __init__.py                    # App factory, extensions
├── config.py                      # Config (dev/prod/test)
├── extensions.py                  # SQLAlchemy, JWT, Limiter instances
├── models/
│   ├── __init__.py
│   ├── user.py                    # User model + methods
│   ├── role.py                    # Role model
│   ├── session.py                 # Session audit table
│   └── campaign_member.py         # M2M User ↔ Campaign (future M4)
├── auth/
│   ├── __init__.py
│   ├── routes.py                  # All /api/auth endpoints
│   ├── validators.py              # Password complexity, email validation
│   ├── decorators.py              # @jwt_required, @limiter.limit
│   └── utils.py                   # Token creation, hashing helpers
├── templates/
│   ├── login.html
│   ├── signup.html
│   └── (other UIs later)
└── static/
    ├── css/
    └── js/
```

### Data Model (SQL DDL)

**Table: roles**
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 'Player', 'DM', 'Admin'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL DEFAULT 1,         -- Foreign key to roles (default=Player)
    mfa_secret VARCHAR(32),                     -- TOTP secret (base32)
    mfa_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
);
```

**Table: sessions** (Audit/Logout history)
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_jti VARCHAR(255) UNIQUE,              -- JWT ID for revocation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,                       -- NULL = active, set = revoked (logout)
    ip_address VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

**Table: mfa_backup_codes** (One-time recovery codes)
```sql
CREATE TABLE mfa_backup_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    used_at TIMESTAMP,                          -- NULL = unused
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
);
```

### User Model (SQLAlchemy ORM)

```python
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), default=1)
    mfa_secret = db.Column(db.String(32))
    mfa_enabled = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = db.relationship('Role', backref='users')
    sessions = db.relationship('Session', backref='user', cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hash + store password"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def get_mfa_totp(self):
        """Return TOTP object for MFA verification"""
        if self.mfa_secret:
            return pyotp.TOTP(self.mfa_secret)
        return None

    def serialize(self, include_email=False):
        """JSON-safe dict for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_email else None,
            'role': self.role.name,
            'mfa_enabled': self.mfa_enabled,
            'created_at': self.created_at.isoformat()
        }
```

### API Contract

#### 1. POST /api/auth/register
```
Request:
{
    "username": "player1",
    "email": "player1@example.com",
    "password": "Secure!Pass123"
}

Response (201):
{
    "id": 1,
    "username": "player1",
    "email": "player1@example.com",
    "role": "Player",
    "mfa_enabled": false,
    "created_at": "2026-03-26T12:00:00Z"
}

Response (400 - Validation):
{ "error": "password must be 8+ chars with uppercase, lowercase, digit, special" }

Response (409 - Conflict):
{ "error": "username or email already exists" }
```

#### 2. POST /api/auth/login
```
Request:
{
    "username": "player1",
    "password": "Secure!Pass123"
}

Response (200 - No MFA):
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
        "id": 1,
        "username": "player1",
        "role": "Player"
    }
}

Response (401 - MFA Required):
{
    "mfa_required": true,
    "temp_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response (401 - Invalid Credentials):
{ "error": "invalid credentials" }

Response (429 - Rate Limited):
{ "error": "too many login attempts, try again in 60 seconds" }
```

#### 3. GET /api/auth/me
```
Request:
Headers: Authorization: Bearer <access_token>

Response (200):
{
    "id": 1,
    "username": "player1",
    "role": "Player",
    "mfa_enabled": false,
    "created_at": "2026-03-26T12:00:00Z"
}

Response (401):
{ "error": "invalid or expired token" }
```

#### 4. POST /api/auth/logout
```
Request:
Headers: Authorization: Bearer <access_token>

Response (200):
{ "success": true }

Behavior: Set revoked_at on session record (or add token to blacklist)
```

#### 5. POST /api/auth/refresh
```
Request:
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response (200):
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response (401):
{ "error": "invalid or expired refresh token" }
```

#### 6. POST /api/auth/mfa/setup (JWT required)
```
Response (200):
{
    "mfa_enabled": false,
    "provisioning_uri": "otpauth://totp/roll%20drauf%20vtt:player1@example.com?secret=JBSWY3DPEBLW64TMMQ...",
    "backup_codes": ["ABC-123", "DEF-456", ...]
}

Note: MFA is not yet enabled. Client stores backup codes, user scans QR from provisioning_uri, then calls /mfa/verify
```

#### 7. POST /api/auth/mfa/verify (JWT required)
```
Request:
{
    "otp": "123456"
}

Response (200):
{ "mfa_enabled": true }

Response (401):
{ "error": "invalid OTP code" }

Behavior: Verify OTP, set user.mfa_enabled = true
```

#### 8. POST /api/auth/mfa/disable (JWT required)
```
Request:
{
    "password": "Secure!Pass123",
    "otp": "123456"
}

Response (200):
{ "mfa_enabled": false }

Behavior: Require password + valid OTP to disable (security measure)
```

### Rate Limiting Config

```python
limiter = Limiter(
    app=app,
    key_func=lambda: request.remote_addr,  # IP-based
    default_limits=["200 per day", "50 per hour"]
)

# Specific limits
limiter.limit("3 per 10 minutes")(auth_routes.register)
limiter.limit("5 per minute")(auth_routes.login)
limiter.limit("10 per minute")(auth_routes.refresh)
```

### Security Config

```python
# In config.py
class Config:
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    BCRYPT_LOG_ROUNDS = 12

    # CORS Whitelist
    CORS_ORIGINS = ['http://localhost:3000', 'https://discord.com']

    # Enforce HTTPS in production
    PREFERRED_URL_SCHEME = 'https'
```

### Pseudocode Flows

**Register Flow:**
```
1. Validate username (3-50 chars, alphanumeric+_)
2. Validate email (RFC 5322 format)
3. Validate password (8+ chars, complexity rules, not blacklisted)
4. Check username & email don't exist (query DB)
5. Create User, set_password (bcrypt hash)
6. Save to DB
7. Return 201 with user.serialize()
8. TODO: Send verification email (M3 Deploy enhancement)
```

**Login Flow:**
```
1. Rate limit check (5/min)
2. Query user by username
3. If not found or password mismatch: Log attempt, return 401
4. If MFA enabled:
   a. Generate temp JWT (short TTL, limited scope)
   b. Return 401 {mfa_required: true}
   c. Client must call /api/auth/mfa/verify with temp JWT
5. Else (no MFA):
   a. Create access_token (1h TTL)
   b. Create refresh_token (7d TTL)
   c. Save session record
   d. Update last_login timestamp
   e. Return 200 {access_token, refresh_token, user}
```

**MFA Verify in Login:**
```
1. Client has temp_token (from 401 response)
2. POST /api/auth/mfa/verify with {otp: "123456"}
3. Validate OTP against user.get_mfa_totp()
4. If valid:
   a. Create real access_token + refresh_token
   b. Save session record
   c. Return 200 {access_token, refresh_token, user}
5. If invalid: return 401
```

---

## Folder & File Structure (New)

```
vtt_app/
├── __init__.py                    # create_app()
├── config.py                      # Dev/Prod/Test config
├── extensions.py                  # db, jwt, limiter, cors instances
├── models/
│   ├── __init__.py                # Import all models
│   ├── user.py
│   ├── role.py
│   ├── session.py
│   └── campaign_member.py         # For M4
├── auth/
│   ├── __init__.py
│   ├── routes.py                  # /api/auth/* endpoints
│   ├── validators.py              # Password, email validators
│   ├── decorators.py              # Custom decorators
│   └── utils.py                   # Token, hash helpers
├── templates/
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
└── static/
    ├── css/style.css
    └── js/auth.js

app.py                             # Entry point (flask run)
requirements.txt                   # Dependencies
.env.example                       # Template for ENV vars
.env                              # (gitignored)
```

---

## Test Strategy (M3 Monitor)

**Unit Tests** (pytest):
- User.set_password + check_password (bcrypt correctness)
- User model validation (username/email unique, required fields)
- Role RBAC logic (user.role permissions)
- JWT token creation/validation (Token TTL, expiry)
- Password validator (complexity rules, blacklist)
- Rate limiter (test bypass protection)

**Integration Tests**:
- POST /api/auth/register happy path + all error cases (400, 409)
- POST /api/auth/login (valid/invalid credentials, rate limit)
- GET /api/auth/me (with/without JWT)
- MFA flow (setup → verify → login with OTP)
- POST /api/auth/logout (revoke token)
- POST /api/auth/refresh (valid/expired tokens)

**Load Test** (200 concurrent users):
- 200 users registering simultaneously
- 200 users logging in simultaneously
- Verify DB integrity (no duplicate users)
- Measure latency (target: <200ms per endpoint)

**Security Test**:
- SQL injection attempts (parameterized queries prevent)
- Weak password rejection
- Rate limit enforcement
- JWT secret not in repo
- HTTPS enforcement in prod

---

## Acceptance Criteria

- [x] User model ORM defined (SQLAlchemy)
- [x] Role model + RBAC defined
- [x] Session audit table designed
- [x] All 8 API endpoints specified + contracts documented
- [x] Pseudocode for register/login/MFA flows
- [x] Folder structure + file organization
- [x] Password validation rules documented
- [x] Rate limiting thresholds configured
- [x] Security measures (JWT, bcrypt, HTTPS) specified
- [x] Test strategy outlined (unit, integration, load, security)
- [x] No implementation code (design only, ready for Deploy phase)

---

## Next Steps

→ Proceed to **M3 Deploy**: Code implementation (models, routes, UI, tests)

