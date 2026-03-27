"""Service helpers for play runtime endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import jsonify

from vtt_app.extensions import db
from vtt_app.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    GameSession,
    SceneLayer,
    SceneStack,
    SessionSnapshot,
    SessionState,
    TokenState,
    User,
)
from vtt_app.utils.time import utcnow

SESSION_TRANSITIONS = {
    "scheduled": {"ready"},
    "ready": {"in_progress"},
    "in_progress": {"paused", "ended"},
    "paused": {"in_progress", "ended"},
    "ended": set(),
}


def parse_iso_datetime(raw_value):
    """Parse ISO timestamp into naive UTC datetime."""
    if not raw_value:
        return None
    try:
        normalized = str(raw_value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def normalize_session_status(raw_status):
    """Normalize legacy status values into runtime states."""
    status = str(raw_status or "").strip().lower()
    if status == "completed":
        return "ended"
    if status == "cancelled":
        return "paused"
    if status in {"scheduled", "ready", "in_progress", "paused", "ended"}:
        return status
    return "scheduled"


def state_status_from_session_status(raw_status):
    """Map session status to session_state status values."""
    status = normalize_session_status(raw_status)
    if status == "in_progress":
        return "live"
    if status == "ended":
        return "completed"
    if status == "paused":
        return "paused"
    return "preparing"


def play_mode_from_session_status(raw_status):
    """Return UI mode identifier from session status."""
    status = normalize_session_status(raw_status)
    if status == "in_progress":
        return "live"
    if status == "paused":
        return "paused"
    if status == "ended":
        return "ended"
    return "waiting"


def is_active_member(campaign: Campaign, user_id: int) -> bool:
    if campaign.owner_id == user_id:
        return True
    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    return member is not None


def get_session_role(campaign: Campaign, user_id: int) -> str | None:
    """Return runtime session role for user."""
    if campaign.owner_id == user_id:
        return "DM"
    member = CampaignMember.query.filter_by(
        campaign_id=campaign.id,
        user_id=user_id,
        status="active",
    ).first()
    if not member:
        return None
    raw_role = str(member.campaign_role or "Player").strip().upper()
    if raw_role in {"DM", "CO_DM", "PLAYER", "OBSERVER"}:
        return raw_role
    if raw_role == "CODM":
        return "CO_DM"
    if raw_role == "CO-DM":
        return "CO_DM"
    return "PLAYER"


def is_operator_role(role: str | None) -> bool:
    return role in {"DM", "CO_DM"}


def is_read_only_mode(session_status, role: str | None) -> bool:
    """Return whether runtime should be read-only for this role."""
    mode = play_mode_from_session_status(session_status)
    if role is None:
        return True
    if role == "OBSERVER":
        return True
    if mode == "waiting" and not is_operator_role(role):
        return True
    if mode == "ended":
        return True
    return False


def coerce_int(raw_value, field_name: str):
    try:
        return int(raw_value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{field_name} must be a number"}), 400)


def get_current_user(user_id):
    if not user_id:
        return None, (jsonify({"error": "authentication required"}), 401)
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None, (jsonify({"error": "authentication required"}), 401)
    user = db.session.get(User, user_id_int)
    if not user or not user.is_active:
        return None, (jsonify({"error": "user not found"}), 404)
    return user, None


def get_campaign_or_404(campaign_id: int):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or not campaign.is_public():
        return None, (jsonify({"error": "campaign not found"}), 404)
    return campaign, None


def get_campaign_session(campaign_id: int, session_id: int):
    game_session = GameSession.query.filter_by(id=session_id, campaign_id=campaign_id).first()
    if not game_session:
        return None, (jsonify({"error": "session not found"}), 404)
    return game_session, None


def ensure_session_state(campaign: Campaign, game_session: GameSession):
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

    state = SessionState(
        game_session_id=game_session.id,
        campaign_id=campaign.id,
        active_map_id=active_map_id,
        state_status=state_status_from_session_status(game_session.status),
        snapshot_json={},
        version=1,
        last_synced_at=utcnow(),
    )
    db.session.add(state)
    db.session.commit()
    return state


def refresh_state_snapshot(state: SessionState):
    active_tokens = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .count()
    )
    state.snapshot_json = {
        "token_count": active_tokens,
        "active_map_id": state.active_map_id,
    }


def serialize_state_payload(game_session: GameSession, state: SessionState):
    active_map = None
    if state.active_map_id:
        active_map = db.session.get(CampaignMap, state.active_map_id)

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


def get_scene_stack(game_session_id: int):
    return SceneStack.query.filter_by(game_session_id=game_session_id).first()


def serialize_scene_stack(scene_stack: SceneStack | None):
    if not scene_stack:
        return None
    layers = (
        SceneLayer.query.filter_by(scene_stack_id=scene_stack.id)
        .order_by(SceneLayer.order_index.asc(), SceneLayer.id.asc())
        .all()
    )
    return {
        **scene_stack.serialize(),
        "layers": [layer.serialize() for layer in layers],
    }


def init_scene_stack(campaign: Campaign, game_session: GameSession, user: User, map_ids: list[int] | None = None):
    existing = get_scene_stack(game_session.id)
    if existing:
        return existing

    query = CampaignMap.query.filter_by(campaign_id=campaign.id, archived_at=None)
    if map_ids:
        query = query.filter(CampaignMap.id.in_(map_ids))
    maps = query.order_by(CampaignMap.created_at.asc()).all()
    if not maps:
        return None

    scene_stack = SceneStack(
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        name=f"{game_session.name} Stack",
        created_by=user.id,
    )
    db.session.add(scene_stack)
    db.session.flush()

    for index, campaign_map in enumerate(maps):
        layer = SceneLayer(
            scene_stack_id=scene_stack.id,
            campaign_map_id=campaign_map.id,
            label=f"Layer {index + 1}",
            order_index=index,
            is_player_visible=True,
        )
        db.session.add(layer)
    db.session.flush()

    first_layer = (
        SceneLayer.query.filter_by(scene_stack_id=scene_stack.id)
        .order_by(SceneLayer.order_index.asc(), SceneLayer.id.asc())
        .first()
    )
    if first_layer:
        scene_stack.active_layer_id = first_layer.id
        game_session.map_id = first_layer.campaign_map_id
        state = ensure_session_state(campaign, game_session)
        state.active_map_id = first_layer.campaign_map_id
        state.bump_version()
        refresh_state_snapshot(state)

    db.session.commit()
    return scene_stack


def activate_scene_layer(campaign: Campaign, game_session: GameSession, layer: SceneLayer):
    scene_stack = db.session.get(SceneStack, layer.scene_stack_id)
    if not scene_stack:
        return None

    scene_stack.active_layer_id = layer.id
    game_session.map_id = layer.campaign_map_id
    state = ensure_session_state(campaign, game_session)
    state.active_map_id = layer.campaign_map_id
    state.bump_version()
    refresh_state_snapshot(state)
    db.session.commit()
    return state


def run_ready_check(campaign: Campaign, game_session: GameSession, session_role: str | None):
    blockers = []
    warnings = []
    if not is_operator_role(session_role):
        blockers.append("operator role required (DM or CO_DM)")

    scene_stack = get_scene_stack(game_session.id)
    if not scene_stack:
        blockers.append("scene stack is not initialized")
        return {"blocking_issues": blockers, "warnings": warnings, "can_start": False}

    layers = (
        SceneLayer.query.filter_by(scene_stack_id=scene_stack.id)
        .order_by(SceneLayer.order_index.asc())
        .all()
    )
    if not layers:
        blockers.append("scene stack has no layers")

    active_layer = None
    if scene_stack.active_layer_id:
        active_layer = db.session.get(SceneLayer, scene_stack.active_layer_id)
    if not active_layer:
        warnings.append("no active scene layer is selected")
    else:
        campaign_map = db.session.get(CampaignMap, active_layer.campaign_map_id)
        if campaign_map and not campaign_map.background_url:
            warnings.append("active layer has no background_url set")

    state = ensure_session_state(campaign, game_session)
    token_count = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .count()
    )
    if token_count == 0:
        warnings.append("no active tokens found in session state")

    return {
        "blocking_issues": blockers,
        "warnings": warnings,
        "can_start": len(blockers) == 0,
    }


def create_session_snapshot(game_session: GameSession, state: SessionState, snapshot_type: str, user_id: int):
    payload = serialize_state_payload(game_session, state)
    snapshot = SessionSnapshot(
        game_session_id=game_session.id,
        snapshot_type=snapshot_type,
        state_version=state.version,
        payload_json=payload,
        created_by=user_id,
    )
    db.session.add(snapshot)
    return snapshot
