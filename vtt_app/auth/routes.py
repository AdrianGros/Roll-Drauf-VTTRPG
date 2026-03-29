"""Auth routes."""
from datetime import datetime, timezone
from flask import request, jsonify
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
from vtt_app.extensions import db, limiter
from vtt_app.models import MFABackupCode, Role, Session, User
from vtt_app.auth import auth_bp
from vtt_app.utils.time import utcnow
from vtt_app.auth.validators import (
    validate_email_address,
    validate_password,
    validate_username,
)


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


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3 per 10 minutes")
def register():
    """Register new user."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

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

    player_role = Role.query.filter_by(name="Player").first() or db.session.get(Role, 1)
    user = User(username=username, email=email, role_id=player_role.id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"user": user.serialize(include_email=True)}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """Login user and set JWT cookies."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    otp = data.get("otp", "").strip()

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
    refresh_token = create_refresh_token(identity=str(user.id))

    user.update_last_login()
    _create_session_from_access_token(user.id, access_token)

    response = jsonify({"user": user.serialize(include_email=True)})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 200


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
    from vtt_app.models import RegistrationKey
    from vtt_app.utils.audit import log_audit

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    registration_key = data.get("registration_key", "").strip()

    # Validate credentials
    is_valid, error = validate_username(username)
    if not is_valid:
        return jsonify({"error": error}), 400

    is_valid, error = validate_email_address(email)
    if not is_valid:
        return jsonify({"error": error}), 400

    is_valid, error = validate_password(password, username, email)
    if not is_valid:
        return jsonify({"error": error}), 400

    # Check username/email uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    # Validate registration key
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

    # Create user with tier from key
    player_role = Role.query.filter_by(name="Player").first() or db.session.get(Role, 1)
    user = User(
        username=username,
        email=email,
        role_id=player_role.id,
        profile_tier=key.tier,
    )
    user.set_password(password)

    # Set quotas based on tier
    tier_quotas = {
        "free": {"storage_gb": 1, "campaigns": 1},
        "player": {"storage_gb": 5, "campaigns": 3},
        "dm": {"storage_gb": 20, "campaigns": 10},
        "headmaster": {"storage_gb": None, "campaigns": None},  # Unlimited
    }

    quota = tier_quotas.get(key.tier, tier_quotas["player"])
    user.storage_quota_gb = quota["storage_gb"]
    user.active_campaigns_quota = quota["campaigns"]

    db.session.add(user)
    db.session.flush()  # Get user ID

    # Consume the key
    key.consume(user.id)

    db.session.commit()

    # Audit log
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

    # Create JWT tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    # Create session
    _create_session_from_access_token(user.id, access_token)

    user.update_last_login()

    response = jsonify({
        "user": user.serialize(include_email=True),
    })
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response, 201
