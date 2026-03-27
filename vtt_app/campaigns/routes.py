"""Campaign and session API routes."""

from datetime import datetime, timezone

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import IntegrityError

from vtt_app.combat import service as combat_service
from vtt_app.campaigns import campaigns_bp
from vtt_app.extensions import db, limiter, socketio
from vtt_app.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    CombatEncounter,
    GameSession,
    InviteToken,
    SessionState,
    TokenState,
    User,
)
from vtt_app.utils.time import utcnow
from vtt_app.utils.realtime import build_event_envelope


def _get_current_user():
    """Return authenticated user or an error response tuple."""
    user_id = get_jwt_identity()
    if not user_id:
        return None, (jsonify({"error": "authentication required"}), 401)

    user = db.session.get(User, int(user_id))
    if not user or not user.is_active:
        return None, (jsonify({"error": "user not found"}), 404)

    return user, None


def _serialize_campaign(campaign: Campaign, user_id: int | None = None):
    """Serialize campaign with frontend-friendly summary fields."""
    active_members = [member for member in campaign.members if member.status == "active"]
    session_count = len(campaign.sessions)

    is_owner = user_id is not None and campaign.owner_id == user_id
    active_membership = None
    if user_id is not None:
        active_membership = next(
            (
                member
                for member in active_members
                if member.user_id == user_id
            ),
            None,
        )

    your_role = "DM" if is_owner else (active_membership.campaign_role if active_membership else None)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "owner": campaign.owner.username,
        "owner_id": campaign.owner_id,
        "status": campaign.status,
        "max_players": campaign.max_players,
        "member_count": len(active_members),
        "players_count": len(active_members),  # Backward compatibility for older templates.
        "session_count": session_count,
        "is_owner": is_owner,
        "is_member": bool(is_owner or active_membership),
        "your_role": your_role,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


def _get_campaign_or_404(campaign_id: int):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or not campaign.is_public():
        return None, (jsonify({"error": "campaign not found"}), 404)
    return campaign, None


def _is_active_member(campaign: Campaign, user_id: int) -> bool:
    if campaign.owner_id == user_id:
        return True

    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    return member is not None


def _is_dm(campaign: Campaign, user_id: int) -> bool:
    if campaign.owner_id == user_id:
        return True

    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    role = str(member.campaign_role).strip().upper() if member else ""
    return role in {"DM", "CO_DM", "CODM"}


def _parse_iso_datetime(raw_value):
    """Parse ISO timestamp into naive UTC datetime."""
    if not raw_value:
        return None

    try:
        normalized = raw_value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except (AttributeError, ValueError):
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _coerce_int(raw_value, field_name: str):
    try:
        return int(raw_value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{field_name} must be a number"}), 400)


def _get_campaign_map_or_404(campaign_id: int, map_id: int, include_archived: bool = False):
    campaign_map = CampaignMap.query.filter_by(id=map_id, campaign_id=campaign_id).first()
    if not campaign_map:
        return None, (jsonify({"error": "map not found"}), 404)
    if campaign_map.archived_at and not include_archived:
        return None, (jsonify({"error": "map not found"}), 404)
    return campaign_map, None


def _ensure_session_state(campaign: Campaign, game_session: GameSession):
    state = SessionState.query.filter_by(game_session_id=game_session.id).first()
    if state:
        return state

    active_map_id = game_session.map_id
    if active_map_id:
        campaign_map = CampaignMap.query.filter_by(
            id=active_map_id,
            campaign_id=campaign.id,
            archived_at=None,
        ).first()
        if not campaign_map:
            active_map_id = None

    if not active_map_id:
        first_map = (
            CampaignMap.query.filter_by(campaign_id=campaign.id, archived_at=None)
            .order_by(CampaignMap.created_at.asc())
            .first()
        )
        active_map_id = first_map.id if first_map else None

    session_status = str(game_session.status or "").strip().lower()
    state_status = "preparing"
    if session_status == "in_progress":
        state_status = "live"
    elif session_status in {"completed", "ended"}:
        state_status = "completed"
    elif session_status in {"cancelled", "paused"}:
        state_status = "paused"

    state = SessionState(
        game_session_id=game_session.id,
        campaign_id=campaign.id,
        active_map_id=active_map_id,
        state_status=state_status,
        snapshot_json={},
        version=1,
        last_synced_at=utcnow(),
    )
    db.session.add(state)
    db.session.commit()
    return state


def _serialize_state_payload(game_session: GameSession, state: SessionState):
    active_map = None
    if state.active_map_id:
        active_map = CampaignMap.query.filter_by(id=state.active_map_id).first()

    tokens = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .order_by(TokenState.id.asc())
        .all()
    )

    return {
        "session": game_session.serialize(),
        "state": state.serialize(),
        "active_map": active_map.serialize() if active_map else None,
        "tokens": [token.serialize() for token in tokens],
    }


def _refresh_state_snapshot(state: SessionState):
    active_tokens = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .count()
    )
    state.snapshot_json = {
        "token_count": active_tokens,
        "active_map_id": state.active_map_id,
    }


def _room_name(campaign_id: int, session_id: int) -> str:
    return f"campaign:{campaign_id}:session:{session_id}"


def _emit_combat_event(campaign_id: int, session_id: int, event_name: str, payload: dict):
    socketio.emit(
        event_name,
        build_event_envelope(campaign_id, session_id, payload),
        room=_room_name(campaign_id, session_id),
    )


def _serialize_combat_state(encounter: CombatEncounter | None, state: SessionState):
    payload = combat_service.serialize_encounter_payload(encounter, include_events=True)
    payload["state_version"] = state.version
    payload["active_map_id"] = state.active_map_id
    return payload


@campaigns_bp.route("/campaigns", methods=["GET"])
@jwt_required()
def list_campaigns():
    """List all public campaigns."""
    user, error = _get_current_user()
    if error:
        return error

    campaigns = (
        Campaign.query.filter(Campaign.deleted_at.is_(None))
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return jsonify([_serialize_campaign(campaign, user.id) for campaign in campaigns]), 200


@campaigns_bp.route("/campaigns", methods=["POST"])
@limiter.limit("10 per hour")
@jwt_required()
def create_campaign():
    """Create new campaign and auto-add creator as active DM member."""
    user, error = _get_current_user()
    if error:
        return error

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    description = data.get("description")
    max_players = data.get("max_players", 6)

    if not name:
        return jsonify({"error": "campaign name required"}), 400

    try:
        max_players = int(max_players)
    except (TypeError, ValueError):
        return jsonify({"error": "max_players must be a number"}), 400

    if max_players < 2 or max_players > 20:
        return jsonify({"error": "max_players must be between 2 and 20"}), 400

    now = utcnow()
    campaign = Campaign(
        name=name,
        description=description,
        owner_id=user.id,
        status="active",
        max_players=max_players,
    )
    db.session.add(campaign)
    db.session.flush()

    owner_member = CampaignMember(
        campaign_id=campaign.id,
        user_id=user.id,
        campaign_role="DM",
        status="active",
        invited_by=user.id,
        invited_at=now,
        accepted_at=now,
        joined_at=now,
    )
    db.session.add(owner_member)
    db.session.commit()

    return jsonify(_serialize_campaign(campaign, user.id)), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>", methods=["GET"])
@jwt_required()
def get_campaign(campaign_id):
    """Get campaign details (members + sessions) for active members."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    members = (
        CampaignMember.query.filter(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.status != "kicked",
        )
        .order_by(CampaignMember.invited_at.desc())
        .all()
    )
    sessions = (
        GameSession.query.filter_by(campaign_id=campaign.id)
        .order_by(GameSession.created_at.desc())
        .all()
    )

    return jsonify(
        {
            "campaign": _serialize_campaign(campaign, user.id),
            "members": [member.serialize() for member in members],
            "sessions": [session.serialize() for session in sessions],
        }
    ), 200


@campaigns_bp.route("/campaigns/mine", methods=["GET"])
@jwt_required()
def list_my_campaigns():
    """List campaigns where current user is an active member."""
    user, error = _get_current_user()
    if error:
        return error

    memberships = CampaignMember.query.filter_by(user_id=user.id, status="active").all()

    campaigns_payload = []
    for membership in memberships:
        campaign = membership.campaign
        if not campaign or not campaign.is_public():
            continue

        serialized = _serialize_campaign(campaign, user.id)
        serialized["your_role"] = membership.campaign_role
        campaigns_payload.append(serialized)

    campaigns_payload.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return jsonify({"campaigns": campaigns_payload}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>", methods=["PUT"])
@limiter.limit("30 per hour")
@jwt_required()
def update_campaign(campaign_id):
    """Update campaign metadata (DM/owner only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "no update payload provided"}), 400

    if "name" in data:
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"error": "campaign name required"}), 400
        campaign.name = name

    if "description" in data:
        campaign.description = data.get("description")

    if "status" in data:
        status = str(data.get("status", "")).strip().lower()
        if status not in {"active", "paused", "archived"}:
            return jsonify({"error": "invalid status"}), 400
        campaign.status = status

    if "max_players" in data:
        try:
            max_players = int(data.get("max_players"))
        except (TypeError, ValueError):
            return jsonify({"error": "max_players must be a number"}), 400

        active_members = CampaignMember.query.filter_by(
            campaign_id=campaign.id,
            status="active",
        ).count()
        if max_players < active_members:
            return jsonify({"error": "max_players cannot be below active member count"}), 400
        if max_players < 2 or max_players > 20:
            return jsonify({"error": "max_players must be between 2 and 20"}), 400
        campaign.max_players = max_players

    db.session.commit()
    return jsonify(_serialize_campaign(campaign, user.id)), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>", methods=["DELETE"])
@limiter.limit("10 per hour")
@jwt_required()
def delete_campaign(campaign_id):
    """Soft-delete campaign (owner only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if campaign.owner_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    campaign.deleted_at = utcnow()
    campaign.status = "archived"
    db.session.commit()
    return jsonify({"message": "campaign deleted"}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/invite", methods=["POST"])
@limiter.limit("40 per hour")
@jwt_required()
def invite_player(campaign_id):
    """Invite player by username and generate invite token (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    username = str(data.get("player_username", "")).strip()
    if not username:
        return jsonify({"error": "player_username required"}), 400

    invited_user = User.query.filter_by(username=username).first()
    if not invited_user:
        return jsonify({"error": "user not found"}), 404

    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=invited_user.id,
    ).first()

    if member and member.status in {"active", "invited"}:
        return jsonify({"error": "user is already a member or invited"}), 409

    now = utcnow()
    if member:
        member.status = "invited"
        member.campaign_role = "Player"
        member.invited_by = user.id
        member.invited_at = now
        member.accepted_at = None
        member.joined_at = None
    else:
        member = CampaignMember(
            campaign_id=campaign.id,
            user_id=invited_user.id,
            campaign_role="Player",
            status="invited",
            invited_by=user.id,
            invited_at=now,
        )
        db.session.add(member)

    token = InviteToken(
        campaign_id=campaign.id,
        token=InviteToken.generate_token(),
        invited_user_email=invited_user.email,
        created_by=user.id,
    )
    db.session.add(token)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "invite could not be created"}), 409

    return jsonify(
        {
            "invite_token": token.token,
            "campaign_id": campaign.id,
            "invited_user": invited_user.username,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        }
    ), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>/accept-invite", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def accept_invite(campaign_id):
    """Accept a campaign invite token."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    data = request.get_json() or {}
    token_value = str(data.get("token", "")).strip()
    if not token_value:
        return jsonify({"error": "token required"}), 400

    token = InviteToken.query.filter_by(campaign_id=campaign.id, token=token_value).first()
    if not token:
        return jsonify({"error": "invalid invite token"}), 400
    if not token.is_valid():
        return jsonify({"error": "invite token expired or already used"}), 400

    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user.id,
    ).first()
    if not member:
        return jsonify({"error": "no invitation found for this user"}), 403
    if member.status == "active":
        return jsonify({"error": "already a campaign member"}), 409
    if member.status != "invited":
        return jsonify({"error": "invitation is no longer valid"}), 403

    if token.invited_user_email and token.invited_user_email.lower() != user.email.lower():
        return jsonify({"error": "invite token does not belong to this user"}), 403

    if not campaign.can_add_player():
        return jsonify({"error": "campaign is full"}), 409

    now = utcnow()
    member.status = "active"
    member.joined_at = now
    member.accepted_at = now
    token.used_at = now
    db.session.commit()

    return jsonify(
        {
            "message": "invite accepted",
            "campaign": _serialize_campaign(campaign, user.id),
        }
    ), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/members", methods=["GET"])
@jwt_required()
def list_campaign_members(campaign_id):
    """List campaign members for active members."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    members = (
        CampaignMember.query.filter(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.status != "kicked",
        )
        .order_by(CampaignMember.invited_at.desc())
        .all()
    )
    return jsonify({"members": [member.serialize() for member in members]}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions", methods=["POST"])
@limiter.limit("40 per hour")
@jwt_required()
def create_session(campaign_id):
    """Create game session (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "session name required"}), 400

    scheduled_at = _parse_iso_datetime(data.get("scheduled_at"))
    if data.get("scheduled_at") and not scheduled_at:
        return jsonify({"error": "scheduled_at must be valid ISO datetime"}), 400

    duration = data.get("duration_minutes")
    if duration is not None:
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            return jsonify({"error": "duration_minutes must be a number"}), 400
        if duration <= 0:
            return jsonify({"error": "duration_minutes must be positive"}), 400

    map_id = data.get("map_id")
    if map_id is not None:
        map_id, error = _coerce_int(map_id, "map_id")
        if error:
            return error

        campaign_map, error = _get_campaign_map_or_404(campaign.id, map_id)
        if error:
            return error
        if campaign_map.archived_at:
            return jsonify({"error": "map is archived"}), 409

    session = GameSession(
        campaign_id=campaign.id,
        name=name,
        scheduled_at=scheduled_at,
        duration_minutes=duration,
        map_id=map_id,
        status="scheduled",
    )
    db.session.add(session)
    db.session.commit()

    return jsonify(session.serialize()), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions", methods=["GET"])
@jwt_required()
def list_sessions(campaign_id):
    """List campaign sessions for active members."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    sessions = (
        GameSession.query.filter_by(campaign_id=campaign.id)
        .order_by(GameSession.created_at.desc())
        .all()
    )
    return jsonify({"sessions": [session.serialize() for session in sessions]}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/maps", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def create_map(campaign_id):
    """Create a reusable campaign map (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "map name required"}), 400

    width, error = _coerce_int(data.get("width"), "width")
    if error:
        return error
    height, error = _coerce_int(data.get("height"), "height")
    if error:
        return error
    if width <= 0 or height <= 0:
        return jsonify({"error": "width and height must be positive"}), 400

    grid_size = data.get("grid_size", 32)
    grid_size, error = _coerce_int(grid_size, "grid_size")
    if error:
        return error
    if grid_size <= 0:
        return jsonify({"error": "grid_size must be positive"}), 400

    grid_type = str(data.get("grid_type", "square")).strip().lower() or "square"
    if grid_type not in {"square"}:
        return jsonify({"error": "unsupported grid_type"}), 400

    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name=name,
        description=data.get("description"),
        grid_type=grid_type,
        grid_size=grid_size,
        width=width,
        height=height,
        background_url=data.get("background_url"),
        fog_enabled=bool(data.get("fog_enabled", False)),
        light_rules=data.get("light_rules") or {},
        created_by=user.id,
    )
    db.session.add(campaign_map)
    db.session.commit()
    return jsonify(campaign_map.serialize()), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>/maps", methods=["GET"])
@jwt_required()
def list_maps(campaign_id):
    """List active campaign maps for members."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    maps = (
        CampaignMap.query.filter_by(campaign_id=campaign.id, archived_at=None)
        .order_by(CampaignMap.created_at.desc())
        .all()
    )
    return jsonify({"maps": [campaign_map.serialize() for campaign_map in maps]}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/maps/<int:map_id>", methods=["GET"])
@jwt_required()
def get_map(campaign_id, map_id):
    """Get a single map definition."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    campaign_map, error = _get_campaign_map_or_404(campaign.id, map_id)
    if error:
        return error
    return jsonify(campaign_map.serialize()), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/maps/<int:map_id>", methods=["PUT"])
@limiter.limit("30 per hour")
@jwt_required()
def update_map(campaign_id, map_id):
    """Update map definition (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    campaign_map, error = _get_campaign_map_or_404(campaign.id, map_id)
    if error:
        return error

    data = request.get_json() or {}
    if not data:
        return jsonify({"error": "no update payload provided"}), 400

    if "name" in data:
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"error": "map name required"}), 400
        campaign_map.name = name

    if "description" in data:
        campaign_map.description = data.get("description")

    if "grid_type" in data:
        grid_type = str(data.get("grid_type", "")).strip().lower()
        if grid_type not in {"square"}:
            return jsonify({"error": "unsupported grid_type"}), 400
        campaign_map.grid_type = grid_type

    if "grid_size" in data:
        grid_size, error = _coerce_int(data.get("grid_size"), "grid_size")
        if error:
            return error
        if grid_size <= 0:
            return jsonify({"error": "grid_size must be positive"}), 400
        campaign_map.grid_size = grid_size

    if "width" in data:
        width, error = _coerce_int(data.get("width"), "width")
        if error:
            return error
        if width <= 0:
            return jsonify({"error": "width must be positive"}), 400
        campaign_map.width = width

    if "height" in data:
        height, error = _coerce_int(data.get("height"), "height")
        if error:
            return error
        if height <= 0:
            return jsonify({"error": "height must be positive"}), 400
        campaign_map.height = height

    if "background_url" in data:
        campaign_map.background_url = data.get("background_url")
    if "fog_enabled" in data:
        campaign_map.fog_enabled = bool(data.get("fog_enabled"))
    if "light_rules" in data:
        campaign_map.light_rules = data.get("light_rules") or {}

    db.session.commit()
    return jsonify(campaign_map.serialize()), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/maps/<int:map_id>", methods=["DELETE"])
@limiter.limit("20 per hour")
@jwt_required()
def archive_map(campaign_id, map_id):
    """Soft-archive campaign map (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    campaign_map, error = _get_campaign_map_or_404(campaign.id, map_id)
    if error:
        return error

    live_state = SessionState.query.filter_by(
        campaign_id=campaign.id,
        active_map_id=campaign_map.id,
        state_status="live",
    ).first()
    if live_state:
        return jsonify({"error": "cannot archive map while live session uses it"}), 409

    campaign_map.archived_at = utcnow()
    db.session.commit()
    return jsonify({"message": "map archived"}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/state", methods=["GET"])
@jwt_required()
def get_session_state(campaign_id, session_id):
    """Return persisted session state + active map + tokens."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error

    state = _ensure_session_state(campaign, game_session)
    return jsonify(_serialize_state_payload(game_session, state)), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/maps/activate", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def activate_session_map(campaign_id, session_id):
    """Activate a campaign map for a session (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error

    data = request.get_json() or {}
    map_id = data.get("map_id")
    if map_id is None:
        return jsonify({"error": "map_id required"}), 400
    map_id, error = _coerce_int(map_id, "map_id")
    if error:
        return error

    campaign_map, error = _get_campaign_map_or_404(campaign.id, map_id)
    if error:
        return error

    state = _ensure_session_state(campaign, game_session)
    state.active_map_id = campaign_map.id
    state.bump_version()
    _refresh_state_snapshot(state)
    game_session.map_id = campaign_map.id
    db.session.commit()

    return jsonify(
        {
            "message": "map activated",
            "state_version": state.version,
            "active_map": campaign_map.serialize(),
        }
    ), 200


def _can_manage_token(campaign: Campaign, user_id: int, token: TokenState) -> bool:
    if _is_dm(campaign, user_id):
        return True
    return token.owner_user_id == user_id


def _parse_token_patch(data: dict, is_dm: bool):
    patch = {}
    allowed_fields = {
        "name",
        "x",
        "y",
        "size",
        "rotation",
        "hp_current",
        "hp_max",
        "initiative",
        "visibility",
        "metadata_json",
    }
    if is_dm:
        allowed_fields.update({"token_type", "owner_user_id", "character_id"})

    for key in allowed_fields:
        if key in data:
            patch[key] = data[key]

    if "x" in patch:
        patch["x"], error = _coerce_int(patch["x"], "x")
        if error:
            return None, error
    if "y" in patch:
        patch["y"], error = _coerce_int(patch["y"], "y")
        if error:
            return None, error
    if "size" in patch:
        patch["size"], error = _coerce_int(patch["size"], "size")
        if error:
            return None, error
        if patch["size"] <= 0:
            return None, (jsonify({"error": "size must be positive"}), 400)
    if "rotation" in patch:
        patch["rotation"], error = _coerce_int(patch["rotation"], "rotation")
        if error:
            return None, error
    if "hp_current" in patch and patch["hp_current"] is not None:
        patch["hp_current"], error = _coerce_int(patch["hp_current"], "hp_current")
        if error:
            return None, error
    if "hp_max" in patch and patch["hp_max"] is not None:
        patch["hp_max"], error = _coerce_int(patch["hp_max"], "hp_max")
        if error:
            return None, error
    if "initiative" in patch and patch["initiative"] is not None:
        patch["initiative"], error = _coerce_int(patch["initiative"], "initiative")
        if error:
            return None, error
    if "owner_user_id" in patch and patch["owner_user_id"] is not None:
        patch["owner_user_id"], error = _coerce_int(patch["owner_user_id"], "owner_user_id")
        if error:
            return None, error
    if "character_id" in patch and patch["character_id"] is not None:
        patch["character_id"], error = _coerce_int(patch["character_id"], "character_id")
        if error:
            return None, error

    if "visibility" in patch:
        visibility = str(patch["visibility"]).strip().lower()
        if visibility not in {"public", "dm_only", "owner_only"}:
            return None, (jsonify({"error": "invalid visibility"}), 400)
        patch["visibility"] = visibility

    if "token_type" in patch:
        token_type = str(patch["token_type"]).strip().lower()
        if token_type not in {"player", "npc", "monster", "object"}:
            return None, (jsonify({"error": "invalid token_type"}), 400)
        patch["token_type"] = token_type

    return patch, None


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/tokens", methods=["POST"])
@limiter.limit("100 per hour")
@jwt_required()
def create_token(campaign_id, session_id):
    """Create persistent token state entry."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    if not state.active_map_id:
        return jsonify({"error": "no active map selected for this session"}), 400

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "token name required"}), 400

    x, error = _coerce_int(data.get("x"), "x")
    if error:
        return error
    y, error = _coerce_int(data.get("y"), "y")
    if error:
        return error

    is_dm_member = _is_dm(campaign, user.id)
    token_type = str(data.get("token_type", "player")).strip().lower()
    if token_type not in {"player", "npc", "monster", "object"}:
        return jsonify({"error": "invalid token_type"}), 400
    if not is_dm_member and token_type != "player":
        return jsonify({"error": "players can only create player tokens"}), 403

    owner_user_id = data.get("owner_user_id")
    if owner_user_id is not None:
        owner_user_id, error = _coerce_int(owner_user_id, "owner_user_id")
        if error:
            return error
    if not is_dm_member and owner_user_id not in {None, user.id}:
        return jsonify({"error": "players can only assign themselves as token owner"}), 403
    if owner_user_id is None and token_type == "player":
        owner_user_id = user.id

    size = data.get("size", 1)
    size, error = _coerce_int(size, "size")
    if error:
        return error
    if size <= 0:
        return jsonify({"error": "size must be positive"}), 400

    rotation = data.get("rotation", 0)
    rotation, error = _coerce_int(rotation, "rotation")
    if error:
        return error

    visibility = str(data.get("visibility", "public")).strip().lower()
    if visibility not in {"public", "dm_only", "owner_only"}:
        return jsonify({"error": "invalid visibility"}), 400

    character_id = data.get("character_id")
    if character_id is not None:
        character_id, error = _coerce_int(character_id, "character_id")
        if error:
            return error

    hp_current = data.get("hp_current")
    if hp_current is not None:
        hp_current, error = _coerce_int(hp_current, "hp_current")
        if error:
            return error

    hp_max = data.get("hp_max")
    if hp_max is not None:
        hp_max, error = _coerce_int(hp_max, "hp_max")
        if error:
            return error

    initiative = data.get("initiative")
    if initiative is not None:
        initiative, error = _coerce_int(initiative, "initiative")
        if error:
            return error

    token = TokenState(
        session_state_id=state.id,
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        map_id=state.active_map_id,
        character_id=character_id,
        owner_user_id=owner_user_id,
        name=name,
        token_type=token_type,
        x=x,
        y=y,
        size=size,
        rotation=rotation,
        hp_current=hp_current,
        hp_max=hp_max,
        initiative=initiative,
        visibility=visibility,
        metadata_json=data.get("metadata_json") or {},
        version=1,
        updated_by=user.id,
    )
    db.session.add(token)
    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    return jsonify({"token": token.serialize(), "state_version": state.version}), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/tokens/<int:token_id>", methods=["PUT"])
@limiter.limit("400 per hour")
@jwt_required()
def update_token(campaign_id, session_id, token_id):
    """Update token state with optimistic concurrency checks."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    token = TokenState.query.filter_by(id=token_id, game_session_id=game_session.id).first()
    if not token or token.deleted_at is not None:
        return jsonify({"error": "token not found"}), 404

    if not _can_manage_token(campaign, user.id, token):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is not None:
        base_version, error = _coerce_int(base_version, "base_version")
        if error:
            return error
        if base_version != token.version:
            return jsonify(
                {
                    "error": "version conflict",
                    "expected_version": token.version,
                    "actual_token": token.serialize(),
                }
            ), 409

    patch, error = _parse_token_patch(data.get("patch", data), _is_dm(campaign, user.id))
    if error:
        return error

    for key, value in patch.items():
        setattr(token, key, value)

    token.map_id = state.active_map_id or token.map_id
    token.version += 1
    token.updated_by = user.id
    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    return jsonify({"token": token.serialize(), "state_version": state.version}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/tokens/<int:token_id>", methods=["DELETE"])
@limiter.limit("100 per hour")
@jwt_required()
def delete_token(campaign_id, session_id, token_id):
    """Soft-delete token state."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    token = TokenState.query.filter_by(id=token_id, game_session_id=game_session.id).first()
    if not token or token.deleted_at is not None:
        return jsonify({"error": "token not found"}), 404

    if not _can_manage_token(campaign, user.id, token):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is not None:
        base_version, error = _coerce_int(base_version, "base_version")
        if error:
            return error
        if base_version != token.version:
            return jsonify(
                {
                    "error": "version conflict",
                    "expected_version": token.version,
                    "actual_token": token.serialize(),
                }
            ), 409

    token.deleted_at = utcnow()
    token.version += 1
    token.updated_by = user.id
    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()
    return jsonify({"message": "token deleted", "state_version": state.version}), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/state", methods=["GET"])
@jwt_required()
def get_combat_state(campaign_id, session_id):
    """Return current or latest combat encounter state for a session."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    encounter = combat_service.get_active_encounter(game_session.id)
    if not encounter:
        encounter = combat_service.get_latest_encounter(game_session.id)

    return jsonify(_serialize_combat_state(encounter, state)), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/start", methods=["POST"])
@limiter.limit("40 per hour")
@jwt_required()
def start_combat(campaign_id, session_id):
    """Start a session-scoped combat encounter (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)
    if not state.active_map_id:
        return jsonify({"error": "no active map selected for this session"}), 400

    existing = combat_service.get_active_encounter(game_session.id)
    if existing:
        return jsonify({"error": "combat already active", "encounter": existing.serialize()}), 409

    data = request.get_json() or {}
    mode = str(data.get("mode", "auto")).strip().lower()

    participant_token_ids = None
    if data.get("participant_token_ids") is not None:
        if not isinstance(data.get("participant_token_ids"), list):
            return jsonify({"error": "participant_token_ids must be a list"}), 400
        participant_token_ids = []
        for raw_token_id in data.get("participant_token_ids"):
            token_id, parse_error = _coerce_int(raw_token_id, "participant_token_ids")
            if parse_error:
                return parse_error
            participant_token_ids.append(token_id)

    encounter, start_error = combat_service.start_encounter(
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        session_state_id=state.id,
        active_map_id=state.active_map_id,
        user_id=user.id,
        mode=mode,
        participant_token_ids=participant_token_ids,
    )
    if start_error:
        return jsonify({"error": start_error}), 400

    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    payload = _serialize_combat_state(encounter, state)
    _emit_combat_event(campaign.id, game_session.id, "combat:started", payload)
    return jsonify(payload), 201


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/initiative", methods=["POST"])
@limiter.limit("80 per hour")
@jwt_required()
def set_combat_initiative(campaign_id, session_id):
    """Set initiative values and reorder encounter participants (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    encounter = combat_service.get_active_encounter(game_session.id)
    if not encounter:
        return jsonify({"error": "no active combat encounter"}), 404

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is None:
        return jsonify({"error": "base_version required"}), 400
    base_version, error = _coerce_int(base_version, "base_version")
    if error:
        return error
    if base_version != encounter.version:
        return jsonify(
            {
                "error": "version conflict",
                "expected_version": encounter.version,
                "actual_encounter": encounter.serialize(),
            }
        ), 409

    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        return jsonify({"error": "entries required"}), 400

    entries = []
    for entry in entries_raw:
        if not isinstance(entry, dict):
            return jsonify({"error": "entries must be objects"}), 400
        token_id, error = _coerce_int(entry.get("token_id"), "token_id")
        if error:
            return error
        initiative, error = _coerce_int(entry.get("initiative"), "initiative")
        if error:
            return error
        entries.append({"token_id": token_id, "initiative": initiative})

    service_error = combat_service.set_initiative(encounter, entries, user.id)
    if service_error:
        return jsonify({"error": service_error}), 400

    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    payload = _serialize_combat_state(encounter, state)
    _emit_combat_event(
        campaign.id,
        game_session.id,
        "combat:updated",
        {"change": "initiative", "state": payload},
    )
    return jsonify(payload), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/turn/advance", methods=["POST"])
@limiter.limit("200 per hour")
@jwt_required()
def advance_combat_turn(campaign_id, session_id):
    """Advance encounter turn pointer (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    encounter = combat_service.get_active_encounter(game_session.id)
    if not encounter:
        return jsonify({"error": "no active combat encounter"}), 404

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is None:
        return jsonify({"error": "base_version required"}), 400
    base_version, error = _coerce_int(base_version, "base_version")
    if error:
        return error
    if base_version != encounter.version:
        return jsonify(
            {
                "error": "version conflict",
                "expected_version": encounter.version,
                "actual_encounter": encounter.serialize(),
            }
        ), 409

    service_error = combat_service.advance_turn(encounter, user.id)
    if service_error:
        return jsonify({"error": service_error}), 400

    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    payload = _serialize_combat_state(encounter, state)
    _emit_combat_event(
        campaign.id,
        game_session.id,
        "combat:turn",
        {
            "encounter_id": encounter.id,
            "round_number": encounter.round_number,
            "turn_index": encounter.turn_index,
            "active_token_id": encounter.active_token_id,
            "version": encounter.version,
            "state": payload,
        },
    )
    return jsonify(payload), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/hp-adjust", methods=["POST"])
@limiter.limit("300 per hour")
@jwt_required()
def adjust_combat_hp(campaign_id, session_id):
    """Apply HP delta to a participant token (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    encounter = combat_service.get_active_encounter(game_session.id)
    if not encounter:
        return jsonify({"error": "no active combat encounter"}), 404

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is None:
        return jsonify({"error": "base_version required"}), 400
    base_version, error = _coerce_int(base_version, "base_version")
    if error:
        return error
    if base_version != encounter.version:
        return jsonify(
            {
                "error": "version conflict",
                "expected_version": encounter.version,
                "actual_encounter": encounter.serialize(),
            }
        ), 409

    target_token_id, error = _coerce_int(data.get("target_token_id"), "target_token_id")
    if error:
        return error
    delta, error = _coerce_int(data.get("delta"), "delta")
    if error:
        return error

    token, service_error = combat_service.adjust_hp(
        encounter=encounter,
        target_token_id=target_token_id,
        delta=delta,
        reason=data.get("reason"),
        user_id=user.id,
    )
    if service_error:
        return jsonify({"error": service_error}), 400

    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    payload = _serialize_combat_state(encounter, state)
    _emit_combat_event(
        campaign.id,
        game_session.id,
        "combat:hp",
        {
            "encounter_id": encounter.id,
            "token_id": token.id,
            "hp_current": token.hp_current,
            "hp_max": token.hp_max,
            "version": encounter.version,
            "state": payload,
        },
    )
    return jsonify(payload), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/combat/end", methods=["POST"])
@limiter.limit("40 per hour")
@jwt_required()
def end_combat(campaign_id, session_id):
    """End the active combat encounter (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    game_session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error
    state = _ensure_session_state(campaign, game_session)

    encounter = combat_service.get_active_encounter(game_session.id)
    if not encounter:
        return jsonify({"error": "no active combat encounter"}), 404

    data = request.get_json() or {}
    base_version = data.get("base_version")
    if base_version is None:
        return jsonify({"error": "base_version required"}), 400
    base_version, error = _coerce_int(base_version, "base_version")
    if error:
        return error
    if base_version != encounter.version:
        return jsonify(
            {
                "error": "version conflict",
                "expected_version": encounter.version,
                "actual_encounter": encounter.serialize(),
            }
        ), 409

    combat_service.end_encounter(encounter, user.id)
    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()

    payload = _serialize_combat_state(encounter, state)
    _emit_combat_event(
        campaign.id,
        game_session.id,
        "combat:ended",
        {
            "encounter_id": encounter.id,
            "ended_at": encounter.ended_at.isoformat() if encounter.ended_at else None,
            "version": encounter.version,
            "state": payload,
        },
    )
    return jsonify(payload), 200


def _get_campaign_session(campaign_id: int, session_id: int):
    session = GameSession.query.filter_by(id=session_id, campaign_id=campaign_id).first()
    if not session:
        return None, (jsonify({"error": "session not found"}), 404)
    return session, None


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/start", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def start_session(campaign_id, session_id):
    """Start a scheduled session (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error

    if session.status != "scheduled":
        return jsonify({"error": "session can only be started from scheduled status"}), 409

    active_session = GameSession.query.filter_by(campaign_id=campaign.id, status="in_progress").first()
    if active_session and active_session.id != session.id:
        return jsonify({"error": "another session is already in progress"}), 409

    session.status = "in_progress"
    session.started_at = utcnow()
    state = _ensure_session_state(campaign, session)
    state.state_status = "live"
    state.bump_version()
    _refresh_state_snapshot(state)
    db.session.commit()
    return jsonify(session.serialize()), 200


@campaigns_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/end", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def end_session(campaign_id, session_id):
    """End an in-progress session (DM only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error

    if not _is_dm(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403

    session, error = _get_campaign_session(campaign.id, session_id)
    if error:
        return error

    if session.status != "in_progress":
        return jsonify({"error": "session can only be ended from in_progress status"}), 409

    session.status = "completed"
    session.ended_at = utcnow()
    state = SessionState.query.filter_by(game_session_id=session.id).first()
    if state:
        state.state_status = "completed"
        state.bump_version()
        _refresh_state_snapshot(state)
    db.session.commit()
    return jsonify(session.serialize()), 200
