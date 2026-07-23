"""Auth routes."""
from datetime import datetime, timedelta, timezone
import secrets
from urllib.parse import quote

from flask import current_app, jsonify, redirect, request, session, url_for
import requests
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)
from vtt.extensions import db, limiter
from vtt.models import DiscordIdentityLink, MFABackupCode, RegistrationKey, Role, Session, User
from vtt.auth import auth_bp
from vtt.auth.discord_oauth import (
    DiscordAuthError,
    build_unique_username,
    build_discord_authorize_url,
    discord_login_enabled,
    exchange_discord_code,
    fetch_discord_profile,
    sanitize_discord_username,
    verify_discord_with_bot,
)
from vtt.utils.time import utcnow
from vtt.auth.validators import (
    validate_email_address,
    validate_password,
    validate_username,
)

REMEMBER_ME_REFRESH_EXPIRES = timedelta(days=30)


def _parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_relative_path(value: str | None, fallback: str = "/dashboard") -> str:
    if not value:
        return fallback
    candidate = str(value).strip()
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return fallback


def _discord_login_redirect(message: str, status_code: int = 302):
    target = f"/login.html?discord_error={quote(message)}"
    return redirect(target, code=status_code)


def _friendly_discord_denial_reason(reason: str | None) -> str:
    normalized = str(reason or "").strip().lower()
    mapping = {
        "not_in_player_list": "Dein Discord-Konto ist im Roll-Drauf Bot nicht als Player freigegeben.",
        "wrong_guild": "Dieses Discord-Konto gehört nicht zum erlaubten Server.",
        "not_member": "Dein Discord-Konto ist aktuell nicht Teil des erlaubten Servers.",
        "already_linked": "Dieses Discord-Konto ist bereits mit einem anderen VTT-Konto verknüpft.",
        "no_key_assignment": "Deinem Discord-Konto wurde noch kein VTT-Zugang vom Bot zugewiesen.",
        "no_valid_key_assignment": "Dein VTT-Zugang ist aktuell nicht freigeschaltet.",
        "access_expired": "Dein zugewiesener VTT-Zugang ist abgelaufen.",
        "access_revoked": "Dein zugewiesener VTT-Zugang wurde widerrufen.",
        "assignment_conflict": "Dieser Discord-Zugang ist bereits mit einem anderen VTT-Konto verknüpft.",
    }
    return mapping.get(normalized, "Dein Discord-Konto ist für diesen Zugang nicht freigegeben.")


def _discord_login_ready() -> bool:
    required_keys = (
        "DISCORD_CLIENT_ID",
        "DISCORD_CLIENT_SECRET",
        "DISCORD_GUILD_ID",
        "DISCORD_BOT_VERIFICATION_URL",
        "DISCORD_BOT_SHARED_SECRET",
    )
    return discord_login_enabled() and all(str(current_app.config.get(key) or "").strip() for key in required_keys)


def _user_has_consumed_registration_key(user_id: int) -> bool:
    return (
        RegistrationKey.query.filter_by(used_by_id=user_id, is_revoked=False)
        .filter(RegistrationKey.used_at.isnot(None))
        .first()
        is not None
    )


def _apply_profile_tier_quota(user: User, tier: str) -> None:
    normalized_tier = str(tier or "player").strip().lower() or "player"
    tier_quotas = {
        "free": {"storage_gb": 1, "campaigns": 1},
        "player": {"storage_gb": 5, "campaigns": 3},
        "dm": {"storage_gb": 20, "campaigns": 10},
        "headmaster": {"storage_gb": None, "campaigns": None},
    }
    quota = tier_quotas.get(normalized_tier, tier_quotas["player"])
    user.profile_tier = normalized_tier
    user.storage_quota_gb = quota["storage_gb"]
    user.active_campaigns_quota = quota["campaigns"]


def _build_discord_assignment_batch_id(discord_user_id: str) -> str:
    return f"discord-assign-{discord_user_id}"


def _resolve_discord_access_assignment(discord_user_id: str) -> tuple[RegistrationKey | None, str | None]:
    keys = (
        RegistrationKey.query
        .filter_by(key_batch_id=_build_discord_assignment_batch_id(discord_user_id))
        .order_by(RegistrationKey.created_at.desc())
        .all()
    )

    if not keys:
        return None, "no_key_assignment"

    active_keys = []
    saw_revoked = False
    saw_expired = False
    now = utcnow()

    for key in keys:
        if key.is_revoked:
            saw_revoked = True
            continue
        # A key's expiry only gates whether it can still be *claimed* — once
        # consumed it already granted access, and that access is a lifetime
        # grant (see registration_keys.expires_at) that shouldn't lapse just
        # because the original invite's expiry window has since passed.
        consumed = key.used_at is not None or key.uses_remaining <= 0
        if not consumed and key.expires_at and now > key.expires_at:
            saw_expired = True
            continue
        active_keys.append(key)

    if active_keys:
        return active_keys[0], None
    if saw_expired:
        return None, "access_expired"
    if saw_revoked:
        return None, "access_revoked"
    return None, "no_valid_key_assignment"


def _find_existing_user_for_discord_identity(discord_user_id: str, discord_email: str | None) -> tuple[User | None, DiscordIdentityLink | None, str | None]:
    link = DiscordIdentityLink.query.filter_by(discord_user_id=discord_user_id).first()
    if link:
        if not link.is_active():
            return None, link, "This Discord link is revoked."
        return link.user, link, None

    assignment, assignment_error = _resolve_discord_access_assignment(discord_user_id)
    if assignment_error:
        return None, None, _friendly_discord_denial_reason(assignment_error)

    user = None
    if assignment and assignment.used_by_id:
        user = db.session.get(User, assignment.used_by_id)

    if not user and discord_email:
        user = User.query.filter_by(email=discord_email).first()

    if not user:
        return None, None, None

    existing_candidate_link = DiscordIdentityLink.query.filter_by(user_id=user.id).first()
    if existing_candidate_link and existing_candidate_link.discord_user_id != discord_user_id and existing_candidate_link.is_active():
        return None, existing_candidate_link, "This VTT account is already linked to a different Discord identity."

    return user, None, None


def _provision_user_from_discord_identity(discord_profile: dict, assignment: RegistrationKey) -> User:
    player_role = Role.query.filter_by(name="Player").first() or db.session.get(Role, 1)
    discord_user_id = str(discord_profile.get("id") or "").strip()
    discord_email = str(discord_profile.get("email") or "").strip().lower()
    base_name = sanitize_discord_username(
        str(
            discord_profile.get("global_name")
            or discord_profile.get("username")
            or discord_profile.get("display_name")
            or ""
        ),
        discord_user_id,
    )
    username = build_unique_username(
        base_name,
        lambda candidate: User.query.filter_by(username=candidate).first() is not None,
        discord_user_id,
    )
    email = discord_email or f"discord_{discord_user_id}@users.roll-drauf.local"

    user = User(
        username=username,
        email=email,
        role_id=player_role.id,
        email_verified=bool(discord_email),
        email_verified_at=utcnow() if discord_email else None,
    )
    user.set_password(secrets.token_urlsafe(32))
    _apply_profile_tier_quota(user, assignment.tier)
    db.session.add(user)
    db.session.flush()
    return user


def _bind_assignment_to_user(assignment: RegistrationKey, user: User) -> None:
    if assignment.used_by_id and assignment.used_by_id != user.id:
        raise DiscordAuthError(_friendly_discord_denial_reason("assignment_conflict"))

    if assignment.uses_remaining > 0:
        assignment.uses_remaining -= 1
    assignment.used_by_id = user.id
    assignment.used_at = assignment.used_at or utcnow()


def _create_session_from_access_token(user_id: int, access_token: str) -> None:
    """Persist session metadata for audit + revocation checks."""
    decoded = decode_token(access_token)
    exp_timestamp = decoded.get("exp")
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)

    session = Session(
        user_id=user_id,
        token_jti=decoded.get("jti"),
        expires_at=expires_at,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )
    db.session.add(session)
    db.session.commit()


def _register_user_with_registration_key(data: dict):
    """Create a user account after validating a registration key."""
    from vtt.utils.audit import log_audit

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    registration_key = data.get("registration_key", "").strip()

    if not registration_key:
        return jsonify({"error": "registration key required"}), 400

    is_valid, error = validate_username(username)
    if not is_valid:
        return jsonify({"error": error}), 400

    is_valid, error = validate_email_address(email)
    if not is_valid:
        return jsonify({"error": error}), 400

    is_valid, error = validate_password(password, username, email)
    if not is_valid:
        return jsonify({"error": error}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    key = RegistrationKey.query.filter_by(key_code=registration_key).first()
    if not key:
        return jsonify({"error": "The spell is not recognized. Please check your key."}), 404

    if not key.is_valid():
        reason = "revoked"
        if key.expires_at and utcnow() > key.expires_at:
            reason = "expired"
        elif key.uses_remaining <= 0:
            reason = "depleted"

        return jsonify({"error": f"The spell has been {reason}. Please contact your Dungeon Master."}), 410

    player_role = Role.query.filter_by(name="Player").first() or db.session.get(Role, 1)
    user = User(
        username=username,
        email=email,
        role_id=player_role.id,
        profile_tier=key.tier,
    )
    user.set_password(password)
    _apply_profile_tier_quota(user, key.tier)

    db.session.add(user)
    db.session.flush()
    key.consume(user.id)
    db.session.commit()

    log_audit(
        action="user_registered_with_key",
        resource_type="user",
        resource_id=user.id,
        details={
            "key_batch_id": key.key_batch_id,
            "tier": key.tier,
        },
        performed_by=user,
    )

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    _create_session_from_access_token(user.id, access_token)
    user.update_last_login()

    response = jsonify({"user": user.serialize(include_email=True)})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 201


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3 per 10 minutes")
def register():
    """Register new user."""
    return _register_user_with_registration_key(request.get_json() or {})


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """Login user and set JWT cookies."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    otp = data.get("otp", "").strip()
    remember_me = _parse_bool(data.get("remember_me", False))

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401

    if not user.is_active:
        return jsonify({"error": "account is inactive"}), 401

    if user.mfa_enabled and not user.verify_mfa_code(otp):
        if not otp:
            return jsonify({"mfa_required": True}), 401
        return jsonify({"error": "invalid MFA code"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(
        identity=str(user.id),
        expires_delta=REMEMBER_ME_REFRESH_EXPIRES if remember_me else None,
    )

    user.update_last_login()
    _create_session_from_access_token(user.id, access_token)

    response = jsonify({"user": user.serialize(include_email=True)})
    cookie_max_age = int(REMEMBER_ME_REFRESH_EXPIRES.total_seconds()) if remember_me else None
    set_access_cookies(response, access_token, max_age=cookie_max_age)
    set_refresh_cookies(response, refresh_token, max_age=cookie_max_age)
    return response, 200


@auth_bp.route("/discord/start", methods=["GET"])
def discord_start():
    """Start Discord OAuth2 login flow."""
    if not _discord_login_ready():
        return _discord_login_redirect("Discord login is not enabled yet.")

    state = secrets.token_urlsafe(32)
    remember_me = _parse_bool(request.args.get("remember_me", False))
    next_path = _sanitize_relative_path(request.args.get("next"), "/dashboard")
    redirect_uri = current_app.config.get("DISCORD_REDIRECT_URI") or url_for("auth.discord_callback", _external=True)
    try:
        authorize_url = build_discord_authorize_url(state=state, redirect_uri=redirect_uri, remember_me=remember_me)
    except DiscordAuthError as exc:
        current_app.logger.warning("Discord login start rejected: %s", exc)
        return _discord_login_redirect(str(exc))

    session["discord_oauth_state"] = state
    session["discord_oauth_next"] = next_path
    session["discord_remember_me"] = remember_me
    session["discord_oauth_redirect_uri"] = redirect_uri
    return redirect(authorize_url)


@auth_bp.route("/discord/status", methods=["GET"])
def discord_status():
    """Expose whether Discord login is configured and enabled."""
    return jsonify({"enabled": _discord_login_ready()}), 200


@auth_bp.route("/discord/callback", methods=["GET"])
def discord_callback():
    """Handle Discord OAuth2 callback and bot-backed authorization."""
    if not _discord_login_ready():
        return _discord_login_redirect("Discord login is not enabled yet.")

    if request.args.get("error"):
        error = request.args.get("error_description") or request.args.get("error") or "Discord login canceled."
        return _discord_login_redirect(f"Discord login failed: {error}")

    expected_state = session.pop("discord_oauth_state", None)
    received_state = request.args.get("state")
    code = request.args.get("code")
    remember_me = _parse_bool(session.pop("discord_remember_me", False))
    next_path = _sanitize_relative_path(session.pop("discord_oauth_next", "/dashboard"), "/dashboard")
    redirect_uri = session.pop("discord_oauth_redirect_uri", None) or current_app.config.get("DISCORD_REDIRECT_URI") or url_for("auth.discord_callback", _external=True)

    if not code:
        return _discord_login_redirect("Discord callback missing authorization code.")
    if not received_state or not expected_state or received_state != expected_state:
        return _discord_login_redirect("Discord login state mismatch. Please try again.")

    try:
        token_data = exchange_discord_code(code, redirect_uri)
        access_token = token_data.get("access_token")
        if not access_token:
            raise DiscordAuthError("Discord token response missing access token")

        discord_profile = fetch_discord_profile(access_token)
        discord_user_id = str(discord_profile.get("id") or "").strip()
        if not discord_user_id:
            raise DiscordAuthError("Discord profile missing user id")

        guild_id = current_app.config.get("DISCORD_GUILD_ID") or ""
        if not guild_id:
            raise DiscordAuthError("Discord guild configuration is missing.")

        bot_payload = {
            "discord_user_id": discord_user_id,
            "guild_id": guild_id,
            "vtt_user_id": None,
            "purpose": "login",
            "state": received_state,
        }
        bot_result = verify_discord_with_bot(bot_payload)

        if not bot_result.get("allowed"):
            reason = _friendly_discord_denial_reason(bot_result.get("reason"))
            return _discord_login_redirect(reason)

        discord_email = str(discord_profile.get("email") or "").strip().lower()
        assignment, assignment_error = _resolve_discord_access_assignment(discord_user_id)
        if assignment_error:
            return _discord_login_redirect(_friendly_discord_denial_reason(assignment_error))

        user, link, user_error = _find_existing_user_for_discord_identity(discord_user_id, discord_email)
        if user_error:
            return _discord_login_redirect(user_error)

        if not user:
            user = _provision_user_from_discord_identity(discord_profile, assignment)

        if not user.is_accessible():
            return _discord_login_redirect("This account is not accessible.")

        _bind_assignment_to_user(assignment, user)

        if not link:
            link = DiscordIdentityLink(
                user_id=user.id,
                discord_user_id=discord_user_id,
            )
            db.session.add(link)
        elif link.user_id != user.id:
            return _discord_login_redirect("This Discord identity is already linked to a different VTT account.")

        link.discord_guild_id = str(bot_result.get("guild_id") or guild_id or "")
        link.discord_username_snapshot = (
            discord_profile.get("global_name")
            or discord_profile.get("username")
            or discord_profile.get("display_name")
            or user.username
        )
        link.bot_verified_role = str(bot_result.get("role") or ("player" if bot_result.get("player") else "player"))
        link.link_status = "linked"
        link.linked_at = link.linked_at or utcnow()
        link.last_verified_at = utcnow()
        link.revoked_at = None

        user.last_login = utcnow()
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(
            identity=str(user.id),
            expires_delta=REMEMBER_ME_REFRESH_EXPIRES if remember_me else None,
        )
        response = redirect(next_path)
        cookie_max_age = int(REMEMBER_ME_REFRESH_EXPIRES.total_seconds()) if remember_me else None
        set_access_cookies(response, access_token, max_age=cookie_max_age)
        set_refresh_cookies(response, refresh_token, max_age=cookie_max_age)
        _create_session_from_access_token(user.id, access_token)
        return response

    except DiscordAuthError as exc:
        return _discord_login_redirect(str(exc))
    except requests.RequestException:
        return _discord_login_redirect("Discord or bot service is temporarily unavailable.")


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True)
def logout():
    """Logout user and clear JWT cookies."""
    user_id = get_jwt_identity()
    if user_id:
        sessions = Session.query.filter_by(user_id=int(user_id), revoked_at=None).all()
        now = utcnow()
        for session in sessions:
            session.revoked_at = now
        db.session.commit()

    response = jsonify({"success": True})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Get current user."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user.serialize(include_email=True)), 200


@auth_bp.route("/check", methods=["GET"])
def check():
    """Check auth state once during page load."""
    verify_jwt_in_request(optional=True)
    identity = get_jwt_identity()
    if identity is None:
        return jsonify({"user": None}), 200

    user = db.session.get(User, int(identity))
    if not user or not user.is_active:
        return jsonify({"user": None}), 200

    return jsonify({"user": user.serialize(include_email=True)}), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True, locations=["cookies"])
@limiter.limit("10 per minute")
def refresh():
    """Refresh access token using refresh cookie."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "user not found or inactive"}), 401

    new_access_token = create_access_token(identity=str(user.id))
    _create_session_from_access_token(user.id, new_access_token)

    response = jsonify({"success": True})
    set_access_cookies(response, new_access_token)
    return response, 200


@auth_bp.route("/mfa/setup", methods=["POST"])
@jwt_required()
def mfa_setup():
    """Setup MFA."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    if not user.mfa_secret:
        user.generate_mfa_secret()

    import secrets

    backup_codes = [secrets.token_hex(3).upper() for _ in range(10)]

    for code in backup_codes:
        code_obj = MFABackupCode(user_id=user.id, code_hash=MFABackupCode.hash_code(code))
        db.session.add(code_obj)

    db.session.commit()

    return jsonify(
        {
            "mfa_enabled": user.mfa_enabled,
            "provisioning_uri": user.get_provisioning_uri(),
            "backup_codes": backup_codes,
        }
    ), 200


@auth_bp.route("/mfa/verify", methods=["POST"])
@jwt_required()
def mfa_verify():
    """Verify MFA."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    data = request.get_json() or {}
    otp = data.get("otp", "").strip()

    if not otp:
        return jsonify({"error": "otp required"}), 400
    if not user.mfa_secret:
        return jsonify({"error": "mfa_not_setup"}), 400
    if not user.verify_mfa_code(otp):
        return jsonify({"error": "invalid MFA code"}), 401

    user.mfa_enabled = True
    db.session.commit()
    return jsonify({"mfa_enabled": True}), 200


@auth_bp.route("/mfa/disable", methods=["POST"])
@jwt_required()
def mfa_disable():
    """Disable MFA."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404

    data = request.get_json() or {}
    password = data.get("password", "")
    otp = data.get("otp", "").strip()

    if not user.check_password(password):
        return jsonify({"error": "invalid password"}), 401
    if not otp or not user.verify_mfa_code(otp):
        return jsonify({"error": "invalid MFA code"}), 401

    user.mfa_enabled = False
    user.mfa_secret = None
    MFABackupCode.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    return jsonify({"mfa_enabled": False}), 200


@auth_bp.route("/register-with-key", methods=["POST"])
@limiter.limit("3 per 10 minutes")
def register_with_key():
    """
    Register a new user using a registration key (M39).

    Expected JSON:
    {
        "username": "newuser",
        "email": "user@example.com",
        "password": "secure_password",
        "registration_key": "SPELL-XXXX-XXXX-XXXX"
    }

    Returns:
        JWT token and user data on success
    """
    return _register_user_with_registration_key(request.get_json() or {})
