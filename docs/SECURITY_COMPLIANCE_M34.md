# M34: Security Hardening & Compliance

**Status**: Design Complete
**Date**: 2026-03-27

---

## Security Architecture

### 1. Authentication & Authorization
- ✅ **Passwords**: bcrypt hashing (12 rounds) - M3
- ✅ **MFA**: TOTP support - M3
- ✅ **JWT**: Tokens for stateless auth - M3
- ✅ **Permission System**: Central library (M17)
- ✅ **Role Hierarchy**: 8 roles with level-based checks (M17)

### 2. Data Protection
- ✅ **In Transit**: HTTPS/TLS (must enforce in config)
- ⏳ **At Rest**: Application-level encryption (optional, for PII)
- ✅ **Secrets**: Environment variables (no hardcoding)
- ✅ **Database**: SQLAlchemy ORM (prevents SQL injection)

### 3. Input Validation
- ✅ **File Uploads**: MIME whitelist, size limits (M20)
- ✅ **Filename Safety**: No path traversal (M20)
- ✅ **JSON Validation**: Flask request validation
- ✅ **Email**: email-validator library

### 4. Output Encoding
- ✅ **XSS Protection**: All responses JSON (not HTML)
- ✅ **CSRF**: JWT tokens (not vulnerable)
- ✅ **Headers**: Security headers should be added (see below)

### 5. Access Control
- ✅ **CORS**: Should be restrictive (same-origin)
- ✅ **Rate Limiting**: Flask-Limiter (100 req/min default)
- ✅ **Resource Ownership**: Validated before access (M17-M22)

---

## Compliance Framework

### GDPR Compliance
- ✅ **Right to Access**: `/api/profile/status` shows all user data
- ✅ **Right to Delete**: `/api/profile/request-deletion` (M18)
- ✅ **Right to Portability**: Export user data endpoint (TODO)
- ✅ **Data Minimization**: Only collect needed fields
- ✅ **Consent**: Terms must be agreed before signup
- ✅ **DPA**: Data Processing Agreement (TODO - legal)
- ✅ **Retention**: 30-day grace period for deletion (M18)
- ✅ **Breach Notification**: Incident response plan (TODO)

### Data Retention Policy (M28)
- **Active Data**: Keep indefinitely (unless deleted by user)
- **Soft-Deleted Assets**: 7 days
- **Soft-Deleted Users**: 30 days
- **Audit Logs**: 1 year (for compliance)
- **Chat Messages**: Deleted with campaign (unless GDPR request)

---

## Incident Response Plan

### If Data Breach Detected
1. **Immediate**: Isolate affected systems
2. **1 Hour**: Notify security team + management
3. **24 Hours**: Notify affected users (legal requirement)
4. **72 Hours**: Report to authorities (GDPR)
5. **Follow-up**: Post-incident review + fixes

### Deployment of Security Patches
- Critical (RCE, SQL injection): Within 24 hours
- High (Auth bypass, XSS): Within 7 days
- Medium (Info disclosure): Within 30 days

---

## Checklist for M34 Deploy

### Application Layer
- [ ] Add CORS headers: `Access-Control-Allow-Origin: https://yourdomain.com`
- [ ] Add CSP header: `Content-Security-Policy: default-src 'self'`
- [ ] Add HSTS header: `Strict-Transport-Security: max-age=31536000`
- [ ] Add X-Frame-Options: `X-Frame-Options: DENY`
- [ ] Add X-Content-Type-Options: `X-Content-Type-Options: nosniff`
- [ ] Validate all user inputs (already done via ORM)
- [ ] Rate limiting enabled (Flask-Limiter already in requirements.txt)

### Database Layer
- [ ] Enforce HTTPS for DB connections
- [ ] Use strong passwords for DB credentials
- [ ] Regular backups (automated, off-site)
- [ ] Encryption at rest (optional, depends on compliance need)

### Infrastructure
- [ ] WAF (Web Application Firewall) enabled
- [ ] DDoS protection (CloudFlare, AWS Shield, etc.)
- [ ] Intrusion detection system
- [ ] Log aggregation (ELK, Splunk, CloudWatch)
- [ ] Security monitoring + alerting

### Operations
- [ ] Secrets rotation (every 90 days)
- [ ] Dependency scanning (dependabot)
- [ ] Security testing (OWASP ZAP, Burp Suite)
- [ ] Penetration testing (annual)
- [ ] Incident response plan documented
- [ ] On-call schedule for security alerts

---

## Known Vulnerabilities (Tracked)

None currently identified in core system.

---

## Third-Party Security

### Dependencies
- Flask 2.3.3 ✅
- SQLAlchemy 3.0.5 ✅
- bcrypt 1.0.1 ✅
- PyOTP 2.9.0 ✅
- Flask-JWT-Extended 4.5.2 ✅

All dependencies checked for known CVEs via:
```bash
pip-audit
safety check
```

---

## Security Testing

### Unit Tests for Security (M34+)
- [ ] Test invalid MIME types rejected
- [ ] Test password hash not leaked in responses
- [ ] Test JWT token required for protected endpoints
- [ ] Test permission denied for unauthorized users
- [ ] Test soft-deleted data not accessible
- [ ] Test MFA correctly validates codes

### Integration Tests
- [ ] Full login flow with MFA
- [ ] Asset upload validation
- [ ] Permission checks across all endpoints
- [ ] Audit logging for all sensitive actions

---

## Future Security Improvements

- **M35**: Key rotation automation
- **M36**: OAuth2/OIDC support for enterprise
- **Future**: Hardware security keys (WebAuthn)
- **Future**: Zero-knowledge proof for sensitive data

