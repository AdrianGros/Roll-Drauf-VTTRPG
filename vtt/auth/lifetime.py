"""Absolute login lifetime (C03): one helper for issuing and validating tokens.

New access and refresh tokens carry the signed integer claims
``vtt_auth_started`` / ``vtt_auth_until`` (exactly one lifetime apart).  Refresh
keeps both values, remember-me never extends them and the client cannot set
them.  Both token JTIs are registered in the existing ``sessions`` table with
``expires_at`` = absolute end, so logout / password change revoke them too.

Legacy tokens (no claims) drain naturally: access at its own ``exp``; refresh is
migrated once using its signed ``iat`` as the anchor, never "now".
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time

from flask import current_app, request
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies

CLAIM_STARTED = "vtt_auth_started"
CLAIM_UNTIL = "vtt_auth_until"
DEFAULT_LIFETIME = timedelta(hours=6)
# Tolerated clock skew between token minting and checking (seconds).
START_SKEW = 60


class AuthLifetimeError(Exception):
    """Token is outside the login policy; ``code`` is a short non-secret reason."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LifetimeInfo:
    token_type: str
    legacy: bool
    started: int | None
    until: int | None  # absolute login end; None for legacy access tokens
    exp: int


@dataclass(frozen=True)
class LoginTokens:
    access: str
    refresh: str
    started: int
    until: int


def _clock() -> float:
    """Single seam for controlled time in tests."""
    return time.time()


def now_ts() -> int:
    return int(_clock())


def now_dt() -> datetime:
    """Naive UTC datetime on the same controlled clock."""
    return ts_to_naive(now_ts())


def ts_to_naive(ts) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)


def naive_to_ts(value: datetime) -> float:
    return value.replace(tzinfo=timezone.utc).timestamp()


def lifetime_seconds() -> int:
    value = current_app.config.get("AUTH_ABSOLUTE_LIFETIME") or DEFAULT_LIFETIME
    return int(value.total_seconds())


def _strict_int(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise AuthLifetimeError("claim_invalid")
    return value


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AuthLifetimeError("claim_invalid")
    return value


def check_payload(payload, *, expected_type=None, allow_expired=False, now=None) -> LifetimeInfo:
    """Validate lifetime, claims and revocation of a decoded JWT payload.

    ``allow_expired`` only waives the short access ``exp`` (table delegation);
    the absolute end, revocation and strict claims are always enforced.
    """
    from vtt.models import Session

    now = now_ts() if now is None else now
    token_type = payload.get("type")
    if token_type not in ("access", "refresh") or (expected_type and token_type != expected_type):
        raise AuthLifetimeError("token_type")
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise AuthLifetimeError("jti_invalid")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise AuthLifetimeError("identity_invalid")
    exp = _number(payload.get("exp"))

    row = Session.query.filter_by(token_jti=jti).first()
    if row is not None:
        if row.user_id != user_id:
            raise AuthLifetimeError("identity_invalid")
        if row.revoked_at is not None:
            raise AuthLifetimeError("revoked")

    has_started = CLAIM_STARTED in payload
    has_until = CLAIM_UNTIL in payload
    if has_started != has_until:
        raise AuthLifetimeError("claims_partial")

    life = lifetime_seconds()
    if has_started:
        started = _strict_int(payload[CLAIM_STARTED])
        until = _strict_int(payload[CLAIM_UNTIL])
        if until - started != life or started > now + START_SKEW:
            raise AuthLifetimeError("claims_implausible")
        if until <= now:
            raise AuthLifetimeError("login_expired")
        if exp > until:
            raise AuthLifetimeError("claims_implausible")
        # Claim-bearing tokens must be registered so logout/revoke reaches them.
        if row is None:
            raise AuthLifetimeError("unregistered")
        row_end = naive_to_ts(row.expires_at)
        if row_end > until or row_end <= now:
            raise AuthLifetimeError("login_expired")
        legacy = False
    elif token_type == "refresh":
        iat = _strict_int(payload.get("iat"))
        started, until, legacy = iat, iat + life, True
        if iat > now + START_SKEW:
            raise AuthLifetimeError("claims_implausible")
        if until <= now:
            raise AuthLifetimeError("login_expired")
        if row is None:
            # Unregistered legacy refresh JTI: honour any user logout that
            # happened at/after its signed issue time (same second = revoked).
            cutoff = (Session.query.filter(Session.user_id == user_id, Session.revoked_at.isnot(None))
                      .order_by(Session.revoked_at.desc()).first())
            if cutoff is not None and naive_to_ts(cutoff.revoked_at) >= iat:
                raise AuthLifetimeError("revoked")
    else:
        started = until = None
        legacy = True

    if exp <= now and not (allow_expired and token_type == "access"):
        raise AuthLifetimeError("token_expired")
    return LifetimeInfo(token_type, legacy, started, until, int(exp))


def token_rejected(payload) -> bool:
    """Blocklist seam: True when the token must not be accepted."""
    try:
        check_payload(payload)
    except AuthLifetimeError:
        return True
    return False


def context_deadline(payload) -> datetime | None:
    """Latest instant a table context issued under this access token may live."""
    info = check_payload(payload, expected_type="access")
    return ts_to_naive(info.until if info.until is not None else info.exp)


def _register(user_id, token_jti, until) -> None:
    from vtt.extensions import db
    from vtt.models import Session

    db.session.add(Session(
        user_id=user_id,
        token_jti=token_jti,
        expires_at=ts_to_naive(until),
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    ))


def _jti(token) -> str:
    from flask_jwt_extended import decode_token
    return decode_token(token)["jti"]


def issue_tokens(user_id, *, started=None, refresh=True) -> LoginTokens:
    """Mint bounded tokens and register their JTIs (commits).

    ``started`` is only passed by the refresh migration with a server-verified
    anchor; it is never taken from the client.
    """
    from vtt.extensions import db

    now = now_ts()
    started = now if started is None else started
    until = started + lifetime_seconds()
    remaining = until - now
    if remaining <= 0:
        raise AuthLifetimeError("login_expired")
    claims = {CLAIM_STARTED: started, CLAIM_UNTIL: until}
    access_ttl = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
    # The final exp is computed here from the one integer anchor and signed
    # explicitly (expires_delta=False: the library adds no relative exp of its
    # own, so a second-boundary between two clocks cannot yield exp > until).
    access = create_access_token(identity=str(user_id), expires_delta=False,
                                 additional_claims={**claims, "exp": min(now + access_ttl, until)})
    refresh_token = None
    if refresh:
        refresh_token = create_refresh_token(identity=str(user_id), expires_delta=False,
                                             additional_claims={**claims, "exp": until})
    _register(user_id, _jti(access), until)
    if refresh_token:
        _register(user_id, _jti(refresh_token), until)
    db.session.commit()
    return LoginTokens(access, refresh_token, started, until)


def cookie_max_age(until) -> int:
    return max(1, int(until - now_ts()))


def expire_legacy_refresh_cookies(response):
    """Delete the pre-C03 refresh JWT/CSRF cookies (path /api/auth/refresh).

    A cookie with the longer old path would otherwise be sent first and shadow
    the new ones.  Name, domain, Secure and SameSite come from the JWT config.
    """
    config = current_app.config
    old_path = config.get("LEGACY_REFRESH_COOKIE_PATH") or "/api/auth/refresh"
    for name in (config.get("JWT_REFRESH_COOKIE_NAME", "refresh_token_cookie"),
                 config.get("JWT_REFRESH_CSRF_COOKIE_NAME", "csrf_refresh_token")):
        response.delete_cookie(name, path=old_path, domain=config.get("JWT_COOKIE_DOMAIN"),
                               secure=config.get("JWT_COOKIE_SECURE", False),
                               samesite=config.get("JWT_COOKIE_SAMESITE"))
    return response


def set_login_cookies(response, tokens: LoginTokens, *, refresh=True):
    max_age = cookie_max_age(tokens.until)
    set_access_cookies(response, tokens.access, max_age=max_age)
    if refresh and tokens.refresh:
        set_refresh_cookies(response, tokens.refresh, max_age=max_age)
        expire_legacy_refresh_cookies(response)
    return response
