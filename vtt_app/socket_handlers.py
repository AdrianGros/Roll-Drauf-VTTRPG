"""Socket.IO event handlers for persisted real-time campaign sessions."""

from collections import defaultdict
from time import monotonic

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import emit, join_room, leave_room

from vtt_app.combat import service as combat_service
from vtt_app.extensions import db
from vtt_app.utils.metrics import increment_counter, increment_labeled_counter
from vtt_app.utils.realtime import build_event_envelope, current_event_seq
from vtt_app.utils.time import utcnow
from vtt_app.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    GameSession,
    Session,
    SessionState,
    TokenState,
    User,
)

_connected_rooms = defaultdict(set)
_seen_client_events = defaultdict(dict)

_DEDUPE_TTL_SECONDS = 120.0
_DEDUPE_MAX_PER_SCOPE = 512


def _room_name(campaign_id: int, session_id: int) -> str:
    return f"campaign:{campaign_id}:session:{session_id}"


def _mod_room_name(campaign_id: int) -> str:
    return f"campaign:{campaign_id}:mods"


def _coerce_int(raw_value, field_name: str):
    try:
        return int(raw_value), None
    except (TypeError, ValueError):
        return None, {"code": "bad_request", "message": f"{field_name} must be a number"}


def _emit_error(code: str, message: str):
    increment_counter("socket_events_total")
    increment_labeled_counter("socket_events_by_name", "state:error")
    emit("state:error", {"code": code, "message": message}, room=request.sid)


def _track_socket_event(event_name: str):
    increment_counter("socket_events_total")
    increment_labeled_counter("socket_events_by_name", event_name)


def _is_session_room(room_name: str) -> bool:
    return room_name.startswith("campaign:") and ":session:" in room_name


def _emit_session_event(event_name: str, campaign_id: int, session_id: int, payload: dict | None = None):
    event_payload = build_event_envelope(campaign_id, session_id, payload, advance=True)
    emit(event_name, event_payload, room=_room_name(campaign_id, session_id))
    return event_payload


def _extract_client_event_id(payload: dict):
    client_event_id = str((payload or {}).get("client_event_id", "")).strip()
    if not client_event_id:
        return None, {"code": "bad_request", "message": "client_event_id required"}
    if len(client_event_id) > 120:
        return None, {"code": "bad_request", "message": "client_event_id too long"}
    return client_event_id, None


def _is_duplicate_client_event(campaign_id: int, session_id: int, user_id: int, client_event_id: str) -> bool:
    now = monotonic()
    scope = _seen_client_events[(campaign_id, session_id, user_id)]

    stale_ids = [event_id for event_id, ts in scope.items() if (now - ts) > _DEDUPE_TTL_SECONDS]
    for event_id in stale_ids:
        scope.pop(event_id, None)

    return client_event_id in scope


def _remember_client_event(campaign_id: int, session_id: int, user_id: int, client_event_id: str):
    now = monotonic()
    scope = _seen_client_events[(campaign_id, session_id, user_id)]
    if len(scope) >= _DEDUPE_MAX_PER_SCOPE:
        oldest = min(scope.items(), key=lambda item: item[1])[0]
        scope.pop(oldest, None)
    scope[client_event_id] = now


def _parse_authenticated_user():
    access_token = request.cookies.get("access_token_cookie")
    if not access_token:
        return None, {"code": "unauthorized", "message": "authentication required"}

    try:
        decoded = decode_token(access_token)
    except Exception:
        return None, {"code": "unauthorized", "message": "invalid token"}

    identity = decoded.get("sub")
    if not identity:
        return None, {"code": "unauthorized", "message": "invalid token identity"}
    try:
        identity_int = int(identity)
    except (TypeError, ValueError):
        return None, {"code": "unauthorized", "message": "invalid token identity"}

    user = db.session.get(User, identity_int)
    if not user or not user.is_active:
        return None, {"code": "unauthorized", "message": "user not found or inactive"}

    token_jti = decoded.get("jti")
    if token_jti:
        session_row = Session.query.filter_by(token_jti=token_jti).first()
        if session_row and session_row.revoked_at is not None:
            return None, {"code": "unauthorized", "message": "token revoked"}

    return user, None


def _get_campaign_session(campaign_id: int, session_id: int):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or not campaign.is_public():
        return None, None, {"code": "not_found", "message": "campaign not found"}

    game_session = GameSession.query.filter_by(id=session_id, campaign_id=campaign_id).first()
    if not game_session:
        return campaign, None, {"code": "not_found", "message": "session not found"}

    return campaign, game_session, None


def _is_active_member(campaign_id: int, user_id: int) -> bool:
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign:
        return False
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        campaign_id=campaign_id,
        user_id=user_id,
        status="active",
    ).first()
    return member is not None


def _is_dm(campaign_id: int, user_id: int) -> bool:
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign:
        return False
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        campaign_id=campaign_id,
        user_id=user_id,
        status="active",
    ).first()
    role = str(member.campaign_role).strip().upper() if member else ""
    return role in {"DM", "CO_DM", "CODM"}


def _normalize_session_status(raw_status: str | None) -> str:
    status = str(raw_status or "").strip().lower()
    if status == "completed":
        return "ended"
    if status == "cancelled":
        return "paused"
    if status in {"scheduled", "ready", "in_progress", "paused", "ended"}:
        return status
    return "scheduled"


def _play_mode_from_session_status(raw_status: str | None) -> str:
    status = _normalize_session_status(raw_status)
    if status == "in_progress":
        return "live"
    if status == "paused":
        return "paused"
    if status == "ended":
        return "ended"
    return "waiting"


def _is_admin(user: User) -> bool:
    if not user or not user.role:
        return False
    return str(user.role.name).lower() == "admin"


def _ensure_session_state(campaign_id: int, game_session: GameSession):
    state = SessionState.query.filter_by(game_session_id=game_session.id).first()
    if state:
        return state

    active_map_id = game_session.map_id
    if active_map_id:
        campaign_map = CampaignMap.query.filter_by(
            id=active_map_id,
            campaign_id=campaign_id,
            archived_at=None,
        ).first()
        if not campaign_map:
            active_map_id = None

    if not active_map_id:
        first_map = (
            CampaignMap.query.filter_by(campaign_id=campaign_id, archived_at=None)
            .order_by(CampaignMap.created_at.asc())
            .first()
        )
        active_map_id = first_map.id if first_map else None

    normalized_status = _normalize_session_status(game_session.status)
    state_status = "preparing"
    if normalized_status == "in_progress":
        state_status = "live"
    elif normalized_status == "ended":
        state_status = "completed"
    elif normalized_status == "paused":
        state_status = "paused"

    state = SessionState(
        game_session_id=game_session.id,
        campaign_id=campaign_id,
        active_map_id=active_map_id,
        state_status=state_status,
        snapshot_json={},
        version=1,
        last_synced_at=utcnow(),
    )
    db.session.add(state)
    db.session.commit()
    return state


def _refresh_state_snapshot(state: SessionState):
    token_count = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .count()
    )
    state.snapshot_json = {
        "token_count": token_count,
        "active_map_id": state.active_map_id,
    }


def _serialize_snapshot(state: SessionState):
    game_session = db.session.get(GameSession, state.game_session_id)
    active_map = db.session.get(CampaignMap, state.active_map_id) if state.active_map_id else None
    tokens = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .order_by(TokenState.id.asc())
        .all()
    )

    return {
        "campaign_id": state.campaign_id,
        "session": game_session.serialize() if game_session else None,
        "state": state.serialize(),
        "active_map": active_map.serialize() if active_map else None,
        "tokens": [token.serialize() for token in tokens],
    }


def _serialize_combat_snapshot(state: SessionState):
    encounter = combat_service.get_active_encounter(state.game_session_id)
    if not encounter:
        encounter = combat_service.get_latest_encounter(state.game_session_id)

    payload = combat_service.serialize_encounter_payload(encounter, include_events=True)
    payload["state_version"] = state.version
    payload["active_map_id"] = state.active_map_id
    return payload


def _parse_token_patch(data: dict, is_dm_member: bool):
    patch = {}
    allowed = {
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
    if is_dm_member:
        allowed.update({"token_type", "owner_user_id", "character_id"})

    for key in allowed:
        if key in data:
            patch[key] = data[key]

    numeric_fields = {
        "x",
        "y",
        "size",
        "rotation",
        "hp_current",
        "hp_max",
        "initiative",
        "owner_user_id",
        "character_id",
    }
    for key in numeric_fields:
        if key in patch and patch[key] is not None:
            coerced, error = _coerce_int(patch[key], key)
            if error:
                return None, error
            patch[key] = coerced

    if "size" in patch and patch["size"] <= 0:
        return None, {"code": "bad_request", "message": "size must be positive"}
    if "visibility" in patch:
        visibility = str(patch["visibility"]).strip().lower()
        if visibility not in {"public", "dm_only", "owner_only"}:
            return None, {"code": "bad_request", "message": "invalid visibility"}
        patch["visibility"] = visibility
    if "token_type" in patch:
        token_type = str(patch["token_type"]).strip().lower()
        if token_type not in {"player", "npc", "monster", "object"}:
            return None, {"code": "bad_request", "message": "invalid token_type"}
        patch["token_type"] = token_type

    return patch, None


def register_socket_handlers(socketio):
    """Register Socket.IO event handlers."""

    @socketio.on("connect")
    def handle_connect(_auth=None):
        _track_socket_event("connect")
        user, error = _parse_authenticated_user()
        if error:
            return False
        emit("connection_response", {"data": "Connected to server", "user_id": user.id}, room=request.sid)

    @socketio.on("disconnect")
    def handle_disconnect():
        _track_socket_event("disconnect")
        for room in _connected_rooms.get(request.sid, set()):
            leave_room(room)
        _connected_rooms.pop(request.sid, None)

    @socketio.on("session:join")
    def handle_session_join(data):
        _track_socket_event("session:join")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        campaign_id, parse_error = _coerce_int((data or {}).get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int((data or {}).get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        room = _room_name(campaign.id, game_session.id)
        existing_rooms = list(_connected_rooms.get(request.sid, set()))
        for existing_room in existing_rooms:
            if _is_session_room(existing_room) and existing_room != room:
                leave_room(existing_room)
                _connected_rooms[request.sid].discard(existing_room)

        join_room(room)
        _connected_rooms[request.sid].add(room)
        increment_counter("socket_reconnect_recoveries_total")

        state = _ensure_session_state(campaign.id, game_session)
        current_seq = current_event_seq(campaign.id, game_session.id)
        emit(
            "session:joined",
            {
                "campaign_id": campaign.id,
                "session_id": game_session.id,
                "server_time": utcnow().isoformat(),
                "event_seq": current_seq,
            },
            room=request.sid,
        )
        snapshot_payload = _serialize_snapshot(state)
        snapshot_payload["event_seq"] = current_seq
        snapshot_payload["server_time"] = utcnow().isoformat()
        emit("state:snapshot", snapshot_payload, room=request.sid)
        emit(
            "play:mode",
            {
                "campaign_id": campaign.id,
                "session_id": game_session.id,
                "status": _normalize_session_status(game_session.status),
                "mode": _play_mode_from_session_status(game_session.status),
                "event_seq": current_seq,
                "server_time": utcnow().isoformat(),
            },
            room=request.sid,
        )

    @socketio.on("session:leave")
    def handle_session_leave(data):
        _track_socket_event("session:leave")
        campaign_id, parse_error = _coerce_int((data or {}).get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int((data or {}).get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        room = _room_name(campaign_id, session_id)
        leave_room(room)
        _connected_rooms[request.sid].discard(room)
        emit("session:left", {"campaign_id": campaign_id, "session_id": session_id}, room=request.sid)

    @socketio.on("mod:join")
    def handle_mod_join(data):
        _track_socket_event("mod:join")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        campaign_id, parse_error = _coerce_int((data or {}).get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign = db.session.get(Campaign, campaign_id)
        if not campaign or not campaign.is_public():
            _emit_error("not_found", "campaign not found")
            return

        if not (_is_dm(campaign.id, user.id) or _is_admin(user)):
            _emit_error("forbidden", "moderator role required")
            return

        room = _mod_room_name(campaign.id)
        join_room(room)
        _connected_rooms[request.sid].add(room)
        emit("mod:joined", {"campaign_id": campaign.id}, room=request.sid)

    @socketio.on("mod:leave")
    def handle_mod_leave(data):
        _track_socket_event("mod:leave")
        campaign_id, parse_error = _coerce_int((data or {}).get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        room = _mod_room_name(campaign_id)
        leave_room(room)
        _connected_rooms[request.sid].discard(room)
        emit("mod:left", {"campaign_id": campaign_id}, room=request.sid)

    @socketio.on("state:request")
    def handle_state_request(data):
        _track_socket_event("state:request")
        increment_counter("socket_resync_requests_total")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        state = _ensure_session_state(campaign.id, game_session)
        snapshot_payload = _serialize_snapshot(state)
        snapshot_payload["event_seq"] = current_event_seq(campaign.id, game_session.id)
        snapshot_payload["server_time"] = utcnow().isoformat()
        emit("state:snapshot", snapshot_payload, room=request.sid)

    @socketio.on("combat:state:request")
    def handle_combat_state_request(data):
        _track_socket_event("combat:state:request")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        state = _ensure_session_state(campaign.id, game_session)
        payload = _serialize_combat_snapshot(state)
        payload["event_seq"] = current_event_seq(campaign.id, game_session.id)
        payload["server_time"] = utcnow().isoformat()
        emit("combat:updated", payload, room=request.sid)

    @socketio.on("map:activate")
    def handle_map_activate(data):
        _track_socket_event("map:activate")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        map_id, parse_error = _coerce_int(payload.get("map_id"), "map_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_dm(campaign.id, user.id):
            _emit_error("forbidden", "dm role required")
            return

        campaign_map = CampaignMap.query.filter_by(
            id=map_id,
            campaign_id=campaign.id,
            archived_at=None,
        ).first()
        if not campaign_map:
            _emit_error("not_found", "map not found")
            return

        state = _ensure_session_state(campaign.id, game_session)
        state.active_map_id = campaign_map.id
        state.bump_version()
        _refresh_state_snapshot(state)
        game_session.map_id = campaign_map.id
        db.session.commit()

        _emit_session_event(
            "map:activated",
            campaign.id,
            game_session.id,
            {"map_id": campaign_map.id, "version": state.version},
        )
        _emit_session_event("state:snapshot", campaign.id, game_session.id, _serialize_snapshot(state))

    @socketio.on("token:create")
    def handle_token_create(data):
        _track_socket_event("token:create")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        client_event_id, event_id_error = _extract_client_event_id(payload)
        if event_id_error:
            _emit_error(event_id_error["code"], event_id_error["message"])
            return
        if _is_duplicate_client_event(campaign.id, game_session.id, user.id, client_event_id):
            emit("state:duplicate", {"client_event_id": client_event_id}, room=request.sid)
            return

        state = _ensure_session_state(campaign.id, game_session)
        if not state.active_map_id:
            _emit_error("bad_request", "no active map selected")
            return

        token_payload = payload.get("token") or {}
        name = str(token_payload.get("name", "")).strip()
        if not name:
            _emit_error("bad_request", "token name required")
            return
        x, parse_error = _coerce_int(token_payload.get("x"), "x")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        y, parse_error = _coerce_int(token_payload.get("y"), "y")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        is_dm_member = _is_dm(campaign.id, user.id)
        token_type = str(token_payload.get("token_type", "player")).strip().lower()
        if token_type not in {"player", "npc", "monster", "object"}:
            _emit_error("bad_request", "invalid token_type")
            return
        if not is_dm_member and token_type != "player":
            _emit_error("forbidden", "players can only create player tokens")
            return

        owner_user_id = token_payload.get("owner_user_id")
        if owner_user_id is not None:
            owner_user_id, parse_error = _coerce_int(owner_user_id, "owner_user_id")
            if parse_error:
                _emit_error(parse_error["code"], parse_error["message"])
                return
        if not is_dm_member and owner_user_id not in {None, user.id}:
            _emit_error("forbidden", "players can only assign themselves as owner")
            return
        if owner_user_id is None and token_type == "player":
            owner_user_id = user.id

        size = token_payload.get("size", 1)
        size, parse_error = _coerce_int(size, "size")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        if size <= 0:
            _emit_error("bad_request", "size must be positive")
            return

        rotation = token_payload.get("rotation", 0)
        rotation, parse_error = _coerce_int(rotation, "rotation")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        hp_current = token_payload.get("hp_current")
        if hp_current is not None:
            hp_current, parse_error = _coerce_int(hp_current, "hp_current")
            if parse_error:
                _emit_error(parse_error["code"], parse_error["message"])
                return

        hp_max = token_payload.get("hp_max")
        if hp_max is not None:
            hp_max, parse_error = _coerce_int(hp_max, "hp_max")
            if parse_error:
                _emit_error(parse_error["code"], parse_error["message"])
                return

        initiative = token_payload.get("initiative")
        if initiative is not None:
            initiative, parse_error = _coerce_int(initiative, "initiative")
            if parse_error:
                _emit_error(parse_error["code"], parse_error["message"])
                return

        visibility = str(token_payload.get("visibility", "public")).strip().lower()
        if visibility not in {"public", "dm_only", "owner_only"}:
            _emit_error("bad_request", "invalid visibility")
            return

        _remember_client_event(campaign.id, game_session.id, user.id, client_event_id)

        token = TokenState(
            session_state_id=state.id,
            campaign_id=campaign.id,
            game_session_id=game_session.id,
            map_id=state.active_map_id,
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
            metadata_json=token_payload.get("metadata_json") or {},
            updated_by=user.id,
            version=1,
        )
        db.session.add(token)
        state.bump_version()
        _refresh_state_snapshot(state)
        db.session.commit()

        _emit_session_event(
            "token:created",
            campaign.id,
            game_session.id,
            {
                "token": token.serialize(),
                "version": token.version,
                "state_version": state.version,
                "client_event_id": client_event_id,
            },
        )

    @socketio.on("token:update")
    def handle_token_update(data):
        _track_socket_event("token:update")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        token_id, parse_error = _coerce_int(payload.get("token_id"), "token_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        state = _ensure_session_state(campaign.id, game_session)
        token = TokenState.query.filter_by(id=token_id, game_session_id=game_session.id).first()
        if not token or token.deleted_at is not None:
            _emit_error("not_found", "token not found")
            return

        is_dm_member = _is_dm(campaign.id, user.id)
        if not is_dm_member and token.owner_user_id != user.id:
            _emit_error("forbidden", "token ownership required")
            return

        client_event_id, event_id_error = _extract_client_event_id(payload)
        if event_id_error:
            _emit_error(event_id_error["code"], event_id_error["message"])
            return
        if _is_duplicate_client_event(campaign.id, game_session.id, user.id, client_event_id):
            emit("state:duplicate", {"client_event_id": client_event_id}, room=request.sid)
            return

        base_version = payload.get("base_version")
        if base_version is None:
            _emit_error("bad_request", "base_version required")
            return

        base_version, parse_error = _coerce_int(base_version, "base_version")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        if base_version != token.version:
            increment_counter("socket_conflicts_total")
            emit(
                "state:conflict",
                {
                    "token_id": token.id,
                    "expected_version": token.version,
                    "actual_token": token.serialize(),
                },
                room=request.sid,
            )
            return

        patch = payload.get("patch", payload)
        parsed_patch, patch_error = _parse_token_patch(patch or {}, is_dm_member)
        if patch_error:
            _emit_error(patch_error["code"], patch_error["message"])
            return

        for key, value in parsed_patch.items():
            setattr(token, key, value)

        _remember_client_event(campaign.id, game_session.id, user.id, client_event_id)

        token.map_id = state.active_map_id or token.map_id
        token.version += 1
        token.updated_by = user.id
        state.bump_version()
        _refresh_state_snapshot(state)
        db.session.commit()

        _emit_session_event(
            "token:updated",
            campaign.id,
            game_session.id,
            {
                "token": token.serialize(),
                "version": token.version,
                "state_version": state.version,
                "client_event_id": client_event_id,
            },
        )

    @socketio.on("token:delete")
    def handle_token_delete(data):
        _track_socket_event("token:delete")
        user, error = _parse_authenticated_user()
        if error:
            _emit_error(error["code"], error["message"])
            return

        payload = data or {}
        campaign_id, parse_error = _coerce_int(payload.get("campaign_id"), "campaign_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        session_id, parse_error = _coerce_int(payload.get("session_id"), "session_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        token_id, parse_error = _coerce_int(payload.get("token_id"), "token_id")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error:
            _emit_error(lookup_error["code"], lookup_error["message"])
            return
        if not _is_active_member(campaign.id, user.id):
            _emit_error("forbidden", "campaign membership required")
            return

        state = _ensure_session_state(campaign.id, game_session)
        token = TokenState.query.filter_by(id=token_id, game_session_id=game_session.id).first()
        if not token or token.deleted_at is not None:
            _emit_error("not_found", "token not found")
            return

        is_dm_member = _is_dm(campaign.id, user.id)
        if not is_dm_member and token.owner_user_id != user.id:
            _emit_error("forbidden", "token ownership required")
            return

        client_event_id, event_id_error = _extract_client_event_id(payload)
        if event_id_error:
            _emit_error(event_id_error["code"], event_id_error["message"])
            return
        if _is_duplicate_client_event(campaign.id, game_session.id, user.id, client_event_id):
            emit("state:duplicate", {"client_event_id": client_event_id}, room=request.sid)
            return

        base_version = payload.get("base_version")
        if base_version is None:
            _emit_error("bad_request", "base_version required")
            return

        base_version, parse_error = _coerce_int(base_version, "base_version")
        if parse_error:
            _emit_error(parse_error["code"], parse_error["message"])
            return
        if base_version != token.version:
            increment_counter("socket_conflicts_total")
            emit(
                "state:conflict",
                {
                    "token_id": token.id,
                    "expected_version": token.version,
                    "actual_token": token.serialize(),
                },
                room=request.sid,
            )
            return

        token.deleted_at = utcnow()
        _remember_client_event(campaign.id, game_session.id, user.id, client_event_id)
        token.version += 1
        token.updated_by = user.id
        state.bump_version()
        _refresh_state_snapshot(state)
        db.session.commit()

        _emit_session_event(
            "token:deleted",
            campaign.id,
            game_session.id,
            {
                "token_id": token.id,
                "version": token.version,
                "state_version": state.version,
                "client_event_id": client_event_id,
            },
        )

    @socketio.on("roll_dice")
    def handle_roll_dice(data: dict, callback=None):
        """Roll dice and return result."""
        _track_socket_event("roll_dice")
        import random
        import re

        user, error = _parse_authenticated_user()
        if error:
            if callable(callback):
                callback({"error": error["message"]})
            return

        dice_str = (data or {}).get("dice", "1d20")
        match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
        if not match:
            if callable(callback):
                callback({"error": "Invalid dice format"})
            return

        num = int(match.group(1))
        sides = int(match.group(2))
        mod = int(match.group(3)) if match.group(3) else 0

        rolls = [random.randint(1, sides) for _ in range(num)]
        total = sum(rolls) + mod

        result = {"rolls": rolls, "modifier": mod, "total": total}
        if callable(callback):
            callback(result)

        player_tag = (data or {}).get("player", "anonymous")
        campaign_id, campaign_parse_error = _coerce_int((data or {}).get("campaign_id"), "campaign_id")
        session_id, session_parse_error = _coerce_int((data or {}).get("session_id"), "session_id")
        if campaign_parse_error or session_parse_error:
            emit("dice_rolled", {"player": player_tag, "dice": dice_str, "result": result}, room=request.sid)
            return

        campaign, game_session, lookup_error = _get_campaign_session(campaign_id, session_id)
        if lookup_error or not campaign or not game_session or not _is_active_member(campaign.id, user.id):
            emit("dice_rolled", {"player": player_tag, "dice": dice_str, "result": result}, room=request.sid)
            return

        _emit_session_event(
            "dice_rolled",
            campaign.id,
            game_session.id,
            {"player": player_tag, "dice": dice_str, "result": result},
        )
