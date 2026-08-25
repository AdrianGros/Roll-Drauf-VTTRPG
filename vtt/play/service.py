"""Service helpers for play runtime endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import jsonify
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db
from vtt.models import (
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
from vtt.utils.time import utcnow

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
    if not user or not user.is_usable():
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


def is_token_visible_to(token: TokenState, role: str | None, viewer_id: int | None) -> bool:
    """Server-side read rule for DM secrets (Playtable-Audit 2026-08-25, P0):
    `dm_only` and foreign `owner_only` tokens must never reach a player's
    wire — the client-side filter in play-ui.js is a display convenience,
    not a boundary."""
    if is_operator_role(role):
        return True
    if token.visibility == "owner_only":
        return viewer_id is not None and token.owner_user_id == viewer_id
    return token.visibility == "public"


def filter_tokens_for(tokens, role: str | None, viewer_id: int | None):
    return [token for token in tokens
            if is_token_visible_to(token, role, viewer_id)]


def is_serialized_token_visible_to(token: dict, role: str | None,
                                   viewer_id: int | None) -> bool:
    """Same read rule as is_token_visible_to, for already-serialized dicts
    (combat payloads carry token serializations, not model instances)."""
    if is_operator_role(role):
        return True
    if token.get("visibility") == "owner_only":
        return viewer_id is not None and token.get("owner_user_id") == viewer_id
    return token.get("visibility") == "public"


def filter_combat_payload(payload: dict | None, role: str | None,
                          viewer_id: int | None) -> dict | None:
    """Playtable-Vordermann 2026-08-25: combat payloads (state + events)
    re-serialize every participant token, so they must apply the same
    role filter as snapshots — including scrubbing hidden token ids from
    initiative_order, masking a hidden active actor, and dropping events
    that reference hidden tokens."""
    if payload is None or is_operator_role(role):
        return payload
    filtered = dict(payload)
    visible = [token for token in payload.get("participants", [])
               if is_serialized_token_visible_to(token, role, viewer_id)]
    visible_ids = {token["id"] for token in visible}
    filtered["participants"] = visible

    encounter = payload.get("encounter")
    if encounter:
        encounter = dict(encounter)
        encounter["initiative_order"] = [
            token_id for token_id in encounter.get("initiative_order", [])
            if token_id in visible_ids]
        if encounter.get("active_token_id") not in visible_ids:
            encounter["active_token_id"] = None
        filtered["encounter"] = encounter

    events = []
    for event in payload.get("events", []):
        event_payload = dict(event.get("payload") or {})
        token_id = event_payload.get("token_id")
        if token_id and token_id not in visible_ids:
            continue
        if (event_payload.get("active_token_id")
                and event_payload["active_token_id"] not in visible_ids):
            event = dict(event)
            event_payload["active_token_id"] = None
            event["payload"] = event_payload
        events.append(event)
    filtered["events"] = events
    return filtered


def serialize_state_payload(game_session: GameSession, state: SessionState,
                            *, role: str | None = None,
                            viewer_id: int | None = None):
    """role=None keeps the unfiltered operator view (DM room broadcasts,
    audits); pass the viewer's session role for anything a player receives."""
    active_map = None
    if state.active_map_id:
        active_map = db.session.get(CampaignMap, state.active_map_id)

    tokens = (
        TokenState.query.filter_by(session_state_id=state.id)
        .filter(TokenState.deleted_at.is_(None))
        .order_by(TokenState.id.asc())
        .all()
    )
    if role is not None and not is_operator_role(role):
        tokens = filter_tokens_for(tokens, role, viewer_id)
    return {
        "session": game_session.serialize(),
        "state": state.serialize(),
        "active_map": active_map.serialize() if active_map else None,
        "tokens": [token.serialize() for token in tokens],
    }


def get_scene_stack(game_session_id: int):
    return SceneStack.query.filter_by(game_session_id=game_session_id).first()


def serialize_scene_stack(scene_stack: SceneStack | None, *,
                          role: str | None = None):
    """role=None keeps the unfiltered operator view; players only receive
    layers marked is_player_visible (Playtable-Audit 2026-08-25, P0)."""
    if not scene_stack:
        return None
    layers = (
        SceneLayer.query.filter_by(scene_stack_id=scene_stack.id)
        .order_by(SceneLayer.order_index.asc(), SceneLayer.id.asc())
        .all()
    )
    if role is not None and not is_operator_role(role):
        layers = [layer for layer in layers if layer.is_player_visible]
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
            # Label from the map's own name, not a generic counter: the
            # page pill and the layer widget both surface this label, and
            # "Layer 1" tells the table nothing (2026-08-25; the add-layer
            # path already labels from the map name — this init path was
            # the leftover).
            label=(campaign_map.name or "").strip()[:120] or f"Layer {index + 1}",
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


def get_or_create_scene_stack(campaign: Campaign, game_session: GameSession, user: User):
    """Return the session's scene stack, creating an empty one if needed."""
    scene_stack = get_scene_stack(game_session.id)
    if scene_stack:
        return scene_stack

    scene_stack = SceneStack(
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        name=f"{game_session.name} Stack",
        created_by=user.id,
    )
    db.session.add(scene_stack)
    db.session.commit()
    return scene_stack


def add_scene_layer(
    campaign: Campaign,
    game_session: GameSession,
    user: User,
    campaign_map_id: int,
    label: str | None = None,
    allow_copy: bool = False,
):
    """Add a single new SceneLayer for an existing CampaignMap.

    UI-Regel (Adrian, 2026-08-25): „Hinzufügen" erzeugt IMMER eine neue
    Seite.  Ist die Karte bereits eine Seite dieses Stacks und allow_copy
    gesetzt, wird die CampaignMap kopiert (gleiche Grafik/Geometrie, neuer
    Name = label, eigene Tokens) statt mit 409 in der Sackgasse „alle
    Karten sind bereits Seiten" zu enden.  Ohne allow_copy bleibt das
    409-Verhalten für Alt-Aufrufer erhalten.

    Returns (scene_stack, layer, error) where error is a Flask response tuple
    on failure and None on success.
    """
    campaign_map = CampaignMap.query.filter_by(
        id=campaign_map_id, campaign_id=campaign.id, archived_at=None
    ).first()
    if not campaign_map:
        return None, None, (jsonify({"error": "campaign map not found"}), 404)

    scene_stack = get_or_create_scene_stack(campaign, game_session, user)

    existing_layer = SceneLayer.query.filter_by(
        scene_stack_id=scene_stack.id, campaign_map_id=campaign_map.id
    ).first()
    if existing_layer and not allow_copy:
        return None, None, (
            jsonify({"error": "campaign map is already a layer in this scene stack"}),
            409,
        )
    if existing_layer:
        copy_name = (label or f"{campaign_map.name} (Kopie)").strip()[:120]
        campaign_map = CampaignMap(
            campaign_id=campaign.id,
            name=copy_name,
            description=campaign_map.description,
            grid_type=campaign_map.grid_type,
            grid_size=campaign_map.grid_size,
            width=campaign_map.width,
            height=campaign_map.height,
            background_url=campaign_map.background_url,
            fog_enabled=campaign_map.fog_enabled,
            light_rules=campaign_map.light_rules,
            created_by=user.id,
        )
        db.session.add(campaign_map)
        db.session.flush()

    max_order = (
        db.session.query(db.func.max(SceneLayer.order_index))
        .filter_by(scene_stack_id=scene_stack.id)
        .scalar()
    )
    next_order_index = (max_order + 1) if max_order is not None else 0

    layer = SceneLayer(
        scene_stack_id=scene_stack.id,
        campaign_map_id=campaign_map.id,
        label=label or campaign_map.name,
        order_index=next_order_index,
        is_player_visible=True,
    )
    db.session.add(layer)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, None, (
            jsonify({"error": "campaign map is already a layer in this scene stack"}),
            409,
        )

    return scene_stack, layer, None


def update_scene_layer(layer: SceneLayer, label: str | None = None, is_player_visible: bool | None = None):
    """Update label and/or player-visibility of a scene layer."""
    if label is not None:
        layer.label = label
    if is_player_visible is not None:
        layer.is_player_visible = is_player_visible
    db.session.commit()
    return layer


def reorder_scene_layers(scene_stack: SceneStack, order_entries: list[tuple[int, int]]):
    """Bulk-apply new order_index values to layers of a scene stack.

    All-or-nothing: validates every layer_id belongs to this scene stack
    before mutating anything. Returns (scene_stack, error).
    """
    layer_ids = [layer_id for layer_id, _ in order_entries]
    layers = SceneLayer.query.filter(
        SceneLayer.scene_stack_id == scene_stack.id,
        SceneLayer.id.in_(layer_ids),
    ).all()
    layers_by_id = {layer.id: layer for layer in layers}

    missing_ids = [layer_id for layer_id in layer_ids if layer_id not in layers_by_id]
    if missing_ids:
        return None, (
            jsonify({"error": f"layer ids not found in this scene stack: {missing_ids}"}),
            400,
        )

    for layer_id, order_index in order_entries:
        layers_by_id[layer_id].order_index = order_index

    db.session.commit()
    return scene_stack, None


def delete_scene_layer(campaign: Campaign, game_session: GameSession, scene_stack: SceneStack, layer: SceneLayer):
    """Delete a scene layer, reassigning the active layer if it was active.

    Returns (scene_stack, state, active_changed). `state` is the
    SessionState if the active map changed as a result, else None.
    """
    was_active = scene_stack.active_layer_id == layer.id
    db.session.delete(layer)
    db.session.flush()

    state = None
    active_changed = False
    if was_active:
        next_layer = (
            SceneLayer.query.filter_by(scene_stack_id=scene_stack.id)
            .order_by(SceneLayer.order_index.asc(), SceneLayer.id.asc())
            .first()
        )
        if next_layer:
            state = activate_scene_layer(campaign, game_session, next_layer)
        else:
            scene_stack.active_layer_id = None
            game_session.map_id = None
            state = ensure_session_state(campaign, game_session)
            state.active_map_id = None
            state.bump_version()
            refresh_state_snapshot(state)
            db.session.commit()
        active_changed = True
    else:
        db.session.commit()

    return scene_stack, state, active_changed


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
