# M3 Discover Output: Auth & User-Management

```
artifact: discover-output
milestone: M3
phase: DISCOVER
status: complete
date: 2026-03-26
```

---

## Input Summary

- **User Request**: Implement Auth & User-Management für Community-Betrieb (200 Mitglieder, 40 Kampagnen).
- **Previous Context**: M1 analyzed VTT features; M1 Apply designed Flask + React architecture.
- **Current Code State**: app.py has fragments of auth (JWT refs), but no persistence, no models, no proper structure.
- **Constraints**: Low-latency, 90% backend test coverage, GDPR compliance, secure defaults.

---

## Current-State Summary

- **Backend**: Flask 2.3.3 + Socket.IO läuft, aber keine Datenbankverbindung.
- **Code Organization**: app.py ist monolithisch, Auth-Code ist fragmentarisch (JWT in app.py referenziert, pyotp imported aber nicht konfiguriert).
- **Persistence**: Kein ORM, in-memory state für maps/tokens.
- **Dependencies**: Minimal (Flask, Socket.IO nur). Fehlend: SQLAlchemy, Bcrypt, JWT-Config, Rate-Limiter, Validierung.

---

## Inventory

| # | Name | Description | Location | Status |
|---|---|---|---|---|
| I1 | User Model | User mit username/email/password_hash/role/mfa_secret | Code | missing |
| I2 | Role Model | Role (Player/DM/Admin) + Permissions | Code | missing |
| I3 | Session Model | Session tracking für JWT + audit log | Code | missing |
| I4 | Campaign_Members | M2M User ↔ Campaign + role-per-campaign | Code | missing |
| I5 | Password Hashing | bcrypt Implementation | Dependencies | missing |
| I6 | JWT Setup | Flask-JWT-Extended konfiguriert | Dependencies | partial (refs in code) |
| I7 | Rate Limiter | Flask-Limiter für signup/login endpoints | Dependencies | missing |
| I8 | MFA/TOTP | pyotp + QR code generation | Dependencies | missing (pyotp imported aber nicht konfiguriert) |
| I9 | Database ORM | Flask-SQLAlchemy + PostgreSQL Driver | Dependencies | missing |
| I10 | Login/Signup UI | HTML + JS form + validation | Frontend | missing |
| I11 | Auth Middleware | @jwt_required(), @limiter.limit() decorators | Code | missing |
| I12 | Password Validation | Rules (8+ chars, complexity) + blacklist | Code | missing |

---

## Dependencies Analysis

### Existing (in requirements.txt)
- Flask==2.3.3 ✓
- flask-socketio==5.3.6 ✓
- python-socketio==5.8.0 ✓

### Required to Add
- **Flask-SQLAlchemy**: ORM für User/Role/Session/Campaign models
- **Flask-Bcrypt**: Password hashing mit salt
- **Flask-JWT-Extended**: JWT creation, validation, refresh tokens
- **Flask-Limiter**: Rate limiting auf endpoints
- **pyotp**: TOTP für MFA/2FA
- **python-dotenv**: Environment variables für secrets
- **email-validator**: Email format validation
- **psycopg2-binary**: PostgreSQL driver (später; SQLite für MVP)
- **werkzeug**: CORS + Security headers

---

## Requirements Analysis

### R1: User Model
- **id** (PK): UUID oder Int auto-increment
- **username**: Unique, 3-50 chars, alphanumeric + underscore, case-insensitive lookup
- **email**: Unique, valid email, lowercase storage
- **password_hash**: bcrypt hash (never plaintext)
- **role**: Foreign key to Role (default: Player)
- **mfa_secret**: Nullable, TOTP secret (base32)
- **mfa_enabled**: Boolean, default False
- **is_active**: Boolean, default True (soft delete support)
- **created_at**: Timestamp (UTC)
- **updated_at**: Timestamp (UTC)
- **last_login**: Nullable timestamp
- **data_export_requested**: For GDPR, track exports

### R2: Role-Based Access Control (RBAC)
Three core roles:
1. **Player**: Join campaigns, roll dice, move own tokens, read chat
2. **DM** (Dungeon Master): Create/edit campaigns, invite players, manage map, moderate, reveal hidden areas
3. **Admin**: User bans, server settings, analytics, all DM powers + moderation

**Permission Model** (for future extension):
- Role has_many Permissions
- Permissions: create_campaign, edit_campaign, delete_campaign, invite_player, etc.

### R3: Authentication Endpoints (5 Core)

1. **POST /api/auth/register**
   - Input: {username, email, password}
   - Output: 201 {id, username, email, role, created_at}
   - Validation: Username unique, email unique, password complexity
   - Rate limit: 3 per 10 min per IP

2. **POST /api/auth/login**
   - Input: {username, password}
   - Output: 200 {access_token, refresh_token, user: {id, username, role}}
   - Validation: Credentials valid
   - Rate limit: 5 per minute per IP
   - MFA: If enabled, return {mfa_required: true}, client must call /api/auth/mfa/verify

3. **POST /api/auth/logout**
   - Input: (JWT required)
   - Output: 200 {success: true}
   - Behavior: Add token to blacklist OR end session record
   - Rate limit: None

4. **POST /api/auth/refresh**
   - Input: {refresh_token}
   - Output: 200 {access_token}
   - Validation: Refresh token valid and not expired
   - Rate limit: 10 per minute per IP

5. **GET /api/auth/me**
   - Input: (JWT required)
   - Output: 200 {id, username, email, role, mfa_enabled, created_at}
   - Validation: JWT valid
   - Rate limit: None

### R4: MFA (Multi-Factor Auth)

- **POST /api/auth/mfa/setup** (JWT required)
  - Output: {mfa_enabled: false, provisioning_uri: "otpauth://...", backup_codes: [code1, code2, ...]}
  - Behavior: Generate TOTP secret, DO NOT enable yet (user must verify)

- **POST /api/auth/mfa/verify** (JWT required)
  - Input: {otp: "123456"}
  - Output: 200 {mfa_enabled: true}
  - Behavior: Verify OTP against secret, enable MFA if valid

- **POST /api/auth/mfa/disable** (JWT required)
  - Input: {password, otp: "123456"}
  - Output: 200 {mfa_enabled: false}
  - Behavior: Require password + valid OTP to disable (prevent account lockout)

### R5: Password Rules (Enforce at signup + reset)
- Min 8 chars, max 128 chars
- At least 1 uppercase (A-Z)
- At least 1 lowercase (a-z)
- At least 1 digit (0-9)
- At least 1 special char (@#$%^&*_-+=)
- Not in common passwords (password, 123456, qwerty, etc.)
- Not username, email, or reverse thereof

### R6: Rate Limiting Thresholds
| Endpoint | Limit | Window | Bypass |
|----------|-------|--------|--------|
| /api/auth/register | 3 | 10 min | None |
| /api/auth/login | 5 | 1 min | None |
| /api/auth/refresh | 10 | 1 min | None |
| /api/auth/password-reset | 1 | 5 min | Email verified |
| Other auth | None | - | - |

### R7: Security Hardening
- **JWT Secret**: Min 32 bytes, random, from ENV var (never repo)
- **Password Hash**: bcrypt with 12+ rounds (default 12)
- **HTTPS Enforced**: Production only (detect in app)
- **CORS**: Whitelist Discord domain + localhost
- **CSRF Protection**: Use session cookies (if applicable) or token validation
- **Session Timeout**: JWT expires 1 hour, refresh token 7 days
- **Logging**: Log failed login attempts (for intrusion detection), NOT passwords

### R8: Data Relations
```
User (1) ← (1:n) → Session           # Audit trail, session history
User (1) ← (n:1) → Role              # One role per user (base), extended via campaign_members
User (n) ← (n:m) → Campaign          # via campaign_members join table
CampaignMember (n) ← (1:n) → User    # User role in specific campaign (DM/Player)
CampaignMember (n) ← (1:n) → Campaign
```

---

## Open Questions

1. **Session Storage in DB**: Track all sessions for audit/logout history, or rely on JWT TTL?
   - *Decision*: Track sessions in DB (session_id, user_id, created_at, expires_at, revoked_at) for audit + explicit logout.

2. **OAuth2 / Third-party Auth**: Include Discord OAuth in M3 or M7?
   - *Decision*: Defer to M7. M3 = local auth only.

3. **Email Verification**: Require email confirmation before login?
   - *Decision*: Yes, but optional (configurable). Send verification link on signup, require click before user is active.

4. **Password Reset**: Include password reset endpoint in M3 Deploy?
   - *Decision*: Yes, basic flow: /api/auth/password-reset → send email link → /api/auth/password-reset-confirm?token=X.

5. **Backup Codes for MFA**: Generate backup codes when MFA setup?
   - *Decision*: Yes, 10 single-use codes, store hashed in DB, display once during setup.

6. **Campaign-Specific Roles**: Can user be Player in campaign A, DM in campaign B?
   - *Decision*: Yes, via campaign_members table. Base user.role is fallback/admin-level.

---

## Risk Assessment

| Risk ID | Risk | Probability | Impact | Mitigation |
|---------|------|------------|--------|-----------|
| SEC-001 | SQL Injection via ORM | Low | Critical | Parameterized queries (SQLAlchemy), input validation |
| SEC-002 | Weak password hash | Low | Critical | Enforce bcrypt 12+ rounds, reject weak passwords |
| SEC-003 | JWT secret leaked in repo | High | Critical | Never commit secrets, use ENV vars, rotate on suspicion |
| SEC-004 | Rate limit bypass (distributed/spoofed IP) | Medium | High | Log bypass attempts, add CAPTCHA on 10+ failures |
| SEC-005 | MFA backup codes leaked | Medium | Medium | Store hashed + salted, display once only, encrypt at rest |
| SEC-006 | Session fixation / token reuse | Low | Medium | Use secure random token generation (secrets module) |
| SEC-007 | Brute force on email/password | High | Medium | Rate limit + progressive delay (exponential backoff) |
| SEC-008 | HTTPS not enforced (dev/prod confusion) | Medium | High | Detect environment, enforce HTTPS in prod + HSTS header |
| SEC-009 | GDPR RTBF (right to be forgotten) | Low | High | Implement user deletion (soft + hard delete options) in M8 |
| SEC-010 | MFA bypass via session hijack | Low | Medium | Bind MFA to IP/User-Agent, require MFA for critical actions |

---

## Acceptance Criteria for M3 Discover

- [x] User model spec defined (fields, types, constraints)
- [x] Role/RBAC model specified (Player/DM/Admin)
- [x] 5 core API endpoints specified (register, login, logout, refresh, me)
- [x] MFA flow defined (setup, verify, disable, backup codes)
- [x] Password rules documented (complexity, blacklist, length)
- [x] Rate limiting thresholds set
- [x] Data relations documented (User ↔ Role, Campaign, Session)
- [x] 10 security risks identified + mitigations
- [x] Dependencies listed (SQLAlchemy, Bcrypt, JWT-Extended, Limiter, pyotp)
- [x] Open questions resolved with decisions
- [x] No implementation code (design only)

---

## Next Steps

→ Proceed to **M3 Apply**: Translate this into DB schema, SQL DDL, API contract pseudocode, folder structure.
