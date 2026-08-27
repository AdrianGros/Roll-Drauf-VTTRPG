"""Play runtime API routes."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from vtt.extensions import db, limiter, socketio
from vtt.models import Character, ChatMessage, InventoryItem, LootTransfer, SceneLayer, TokenLoot, TokenState
from vtt.play import play_bp
from vtt.play.actions import execute_action, get_action_catalog
from vtt.utils.metrics import increment_counter, increment_labeled_counter
from vtt.utils.realtime import (
    build_event_envelope,
    dm_room,
    players_room,
    sibling_envelope,
    user_room,
)
from vtt.utils.time import utcnow
from vtt.play.service import (
    SESSION_TRANSITIONS,
    activate_scene_layer,
    add_scene_layer,
    coerce_int,
    create_session_snapshot,
    delete_scene_layer,
    ensure_session_state,
    get_campaign_or_404,
    get_campaign_session,
    get_current_user,
    get_scene_stack,
    get_session_role,
    init_scene_stack,
    is_active_member,
    is_operator_role,
    is_read_only_mode,
    normalize_session_status,
    play_mode_from_session_status,
    refresh_state_snapshot,
    reorder_scene_layers,
    run_ready_check,
    serialize_scene_stack,
    serialize_state_payload,
    state_status_from_session_status,
    update_scene_layer,
)


def _emit_scoped_state_snapshot(campaign, game_session, state):
    """Playtable-Audit 2026-08-25 (P0): room-wide state snapshots are
    role-scoped.  Operators get the full view; owners of owner_only tokens
    get their personal view via their user room; the players room gets the
    public view.  All variants share ONE event_seq, and the client DROPS
    a repeated seq as stale — so the most specific variant must be
    emitted FIRST (an owner then discards the later public variant)."""
    full = serialize_state_payload(game_session, state)
    envelope = build_event_envelope(campaign.id, game_session.id, full)
    socketio.emit("state:snapshot", envelope,
                  room=dm_room(campaign.id, game_session.id))

    owner_ids = {
        token.owner_user_id
        for token in TokenState.query.filter_by(
            session_state_id=state.id, visibility="owner_only")
        .filter(TokenState.deleted_at.is_(None))
        .all()
        if token.owner_user_id is not None
    }
    for owner_id in owner_ids:
        if is_operator_role(get_session_role(campaign, owner_id)):
            continue  # operators already hold the full view
        owner_view = serialize_state_payload(game_session, state,
                                             role="PLAYER",
                                             viewer_id=owner_id)
        socketio.emit("state:snapshot", sibling_envelope(envelope, owner_view),
                      room=user_room(campaign.id, game_session.id, owner_id))

    public_view = serialize_state_payload(game_session, state,
                                          role="PLAYER", viewer_id=None)
    socketio.emit("state:snapshot", sibling_envelope(envelope, public_view),
                  room=players_room(campaign.id, game_session.id))


def _emit_scoped_layers_updated(campaign, game_session, scene_stack):
    """scene:layers_updated, role-scoped (hidden layers stay with the DM)."""
    envelope = build_event_envelope(campaign.id, game_session.id,
                                    serialize_scene_stack(scene_stack))
    socketio.emit("scene:layers_updated", envelope,
                  room=dm_room(campaign.id, game_session.id))
    socketio.emit(
        "scene:layers_updated",
        sibling_envelope(envelope,
                         serialize_scene_stack(scene_stack, role="PLAYER")),
        room=players_room(campaign.id, game_session.id))


def _room_name(campaign_id: int, session_id: int) -> str:
    return f"campaign:{campaign_id}:session:{session_id}"


def _serialize_session_runtime(session):
    payload = session.serialize()
    payload["runtime_status"] = normalize_session_status(session.status)
    return payload


def _get_context(campaign_id: int, session_id: int):
    user_id = get_jwt_identity()
    user, error = get_current_user(user_id)
    if error:
        return None, None, None, error

    campaign, error = get_campaign_or_404(campaign_id)
    if error:
        return None, None, None, error

    game_session, error = get_campaign_session(campaign.id, session_id)
    if error:
        return None, None, None, error

    if not is_active_member(campaign, user.id):
        return None, None, None, (jsonify({"error": "forbidden"}), 403)

    session_role = get_session_role(campaign, user.id)
    return user, campaign, game_session, session_role


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/bootstrap", methods=["GET"])
@jwt_required()
def bootstrap_play_runtime(campaign_id, session_id):
    """Return all data required to initialize /play runtime."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role

    state = ensure_session_state(campaign, game_session)
    scene_stack = get_scene_stack(game_session.id)
    mode = play_mode_from_session_status(game_session.status)
    read_only = is_read_only_mode(game_session.status, session_role)

    payload = {
        "user": {
            "id": user.id,
            "username": user.username,
        },
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
        },
        "session": _serialize_session_runtime(game_session),
        "session_role": session_role,
        "mode": mode,
        "read_only": read_only,
        # Playtable-Audit 2026-08-25 (P0): the bootstrap is role-scoped —
        # players never receive dm_only/foreign-owner tokens or hidden layers.
        "scene_stack": serialize_scene_stack(scene_stack, role=session_role),
        "state_payload": serialize_state_payload(
            game_session, state, role=session_role, viewer_id=user.id),
        "action_catalog": get_action_catalog(),
        # Last 30 visible chat messages, newest first (same shape the live
        # "chat:message_sent" broadcast uses), so a page reload no longer
        # wipes the table conversation (robot audit 2026-08-23).
        "chat_history": [
            {
                "message_id": row.id,
                "message": row.content,
                "sender_id": row.author_user_id,
                "sender_name": row.author.username if row.author else "player",
                "timestamp": row.created_at.isoformat() if row.created_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in ChatMessage.query.filter_by(
                game_session_id=game_session.id,
                deleted_at=None,
            )
            .filter(ChatMessage.moderation_state == "visible")
            .order_by(ChatMessage.created_at.desc())
            .limit(30)
            .all()
        ],
        "server_time": utcnow().isoformat(),
    }
    return jsonify(payload), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/ready-check", methods=["GET"])
@jwt_required()
def play_ready_check(campaign_id, session_id):
    """Run soft readiness checks before starting live play."""
    _user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role

    result = run_ready_check(campaign, game_session, session_role)
    result["session_status"] = normalize_session_status(game_session.status)
    result["session_role"] = session_role
    return jsonify(result), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/init", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def play_init_scene_stack(campaign_id, session_id):
    """Initialize scene stack and layers for a session."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    map_ids = None
    if data.get("map_ids") is not None:
        if not isinstance(data.get("map_ids"), list):
            return jsonify({"error": "map_ids must be a list"}), 400
        map_ids = []
        for raw_map_id in data.get("map_ids"):
            map_id, parse_error = coerce_int(raw_map_id, "map_ids")
            if parse_error:
                return parse_error
            map_ids.append(map_id)

    scene_stack = init_scene_stack(campaign, game_session, user, map_ids=map_ids)
    if not scene_stack:
        return jsonify({"error": "no campaign maps available to initialize scene stack"}), 409

    state = ensure_session_state(campaign, game_session)
    room = _room_name(campaign.id, game_session.id)
    socketio.emit(
        "scene:layer_activated",
        build_event_envelope(campaign.id, game_session.id, {
            "campaign_id": campaign.id,
            "session_id": game_session.id,
            "scene_stack_id": scene_stack.id,
            "active_layer_id": scene_stack.active_layer_id,
            "active_map_id": state.active_map_id,
            "state_version": state.version,
        }),
        room=room,
    )
    _emit_scoped_state_snapshot(campaign, game_session, state)

    return jsonify({"scene_stack": serialize_scene_stack(scene_stack)}), 201


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers/<int:layer_id>/activate", methods=["POST"])
@limiter.limit("60 per hour")
@jwt_required()
def play_activate_layer(campaign_id, session_id, layer_id):
    """Activate one scene layer and sync active map to session state."""
    _user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    scene_stack = get_scene_stack(game_session.id)
    if not scene_stack:
        return jsonify({"error": "scene stack not initialized"}), 409

    layer = SceneLayer.query.filter_by(id=layer_id, scene_stack_id=scene_stack.id).first()
    if not layer:
        return jsonify({"error": "scene layer not found"}), 404

    state = activate_scene_layer(campaign, game_session, layer)
    if not state:
        return jsonify({"error": "failed to activate layer"}), 500

    room = _room_name(campaign.id, game_session.id)
    socketio.emit(
        "scene:layer_activated",
        build_event_envelope(campaign.id, game_session.id, {
            "campaign_id": campaign.id,
            "session_id": game_session.id,
            "scene_stack_id": scene_stack.id,
            "active_layer_id": layer.id,
            "active_map_id": layer.campaign_map_id,
            "state_version": state.version,
        }),
        room=room,
    )
    _emit_scoped_state_snapshot(campaign, game_session, state)

    return jsonify(
        {
            "scene_stack": serialize_scene_stack(scene_stack),
            "active_layer": layer.serialize(),
            "state": state.serialize(),
        }
    ), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers", methods=["POST"])
@limiter.limit("60 per hour")
@jwt_required()
def play_add_scene_layer(campaign_id, session_id):
    """Add a single new scene layer from an existing CampaignMap."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    campaign_map_id, parse_error = coerce_int(data.get("campaign_map_id"), "campaign_map_id")
    if parse_error:
        return parse_error

    label = data.get("label")
    if label is not None:
        label = str(label).strip() or None

    allow_copy = bool(data.get("allow_copy"))
    scene_stack, layer, error = add_scene_layer(
        campaign, game_session, user, campaign_map_id,
        label=label, allow_copy=allow_copy)
    if error:
        return error

    _emit_scoped_layers_updated(campaign, game_session, scene_stack)

    return jsonify({"scene_stack": serialize_scene_stack(scene_stack), "layer": layer.serialize()}), 201


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers/reorder", methods=["PUT"])
@limiter.limit("60 per hour")
@jwt_required()
def play_reorder_scene_layers(campaign_id, session_id):
    """Bulk reorder scene layers within a session's scene stack."""
    _user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    scene_stack = get_scene_stack(game_session.id)
    if not scene_stack:
        return jsonify({"error": "scene stack not initialized"}), 409

    data = request.get_json() or {}
    raw_order = data.get("order")
    if not isinstance(raw_order, list) or not raw_order:
        return jsonify({"error": "order must be a non-empty list"}), 400

    order_entries = []
    for entry in raw_order:
        if not isinstance(entry, dict):
            return jsonify({"error": "each order entry must be an object"}), 400
        layer_id, parse_error = coerce_int(entry.get("layer_id"), "layer_id")
        if parse_error:
            return parse_error
        order_index, parse_error = coerce_int(entry.get("order_index"), "order_index")
        if parse_error:
            return parse_error
        order_entries.append((layer_id, order_index))

    scene_stack, error = reorder_scene_layers(scene_stack, order_entries)
    if error:
        return error

    _emit_scoped_layers_updated(campaign, game_session, scene_stack)

    return jsonify({"scene_stack": serialize_scene_stack(scene_stack)}), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers/<int:layer_id>", methods=["PUT"])
@limiter.limit("60 per hour")
@jwt_required()
def play_update_scene_layer(campaign_id, session_id, layer_id):
    """Update a scene layer's label and/or player visibility."""
    _user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    scene_stack = get_scene_stack(game_session.id)
    if not scene_stack:
        return jsonify({"error": "scene stack not initialized"}), 409

    layer = SceneLayer.query.filter_by(id=layer_id, scene_stack_id=scene_stack.id).first()
    if not layer:
        return jsonify({"error": "scene layer not found"}), 404

    data = request.get_json() or {}

    label = None
    if "label" in data:
        raw_label = data.get("label")
        label = str(raw_label).strip() if raw_label is not None else ""
        if not label:
            return jsonify({"error": "label must be a non-empty string"}), 400

    is_player_visible = None
    if "is_player_visible" in data:
        raw_visible = data.get("is_player_visible")
        if not isinstance(raw_visible, bool):
            return jsonify({"error": "is_player_visible must be a boolean"}), 400
        is_player_visible = raw_visible

    layer = update_scene_layer(layer, label=label, is_player_visible=is_player_visible)

    _emit_scoped_layers_updated(campaign, game_session, scene_stack)

    return jsonify({"scene_stack": serialize_scene_stack(scene_stack), "layer": layer.serialize()}), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/scene-stack/layers/<int:layer_id>", methods=["DELETE"])
@limiter.limit("60 per hour")
@jwt_required()
def play_delete_scene_layer(campaign_id, session_id, layer_id):
    """Remove a scene layer, promoting a new active layer if needed."""
    _user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    scene_stack = get_scene_stack(game_session.id)
    if not scene_stack:
        return jsonify({"error": "scene stack not initialized"}), 409

    layer = SceneLayer.query.filter_by(id=layer_id, scene_stack_id=scene_stack.id).first()
    if not layer:
        return jsonify({"error": "scene layer not found"}), 404

    scene_stack, state, active_changed = delete_scene_layer(campaign, game_session, scene_stack, layer)

    _emit_scoped_layers_updated(campaign, game_session, scene_stack)
    if active_changed and state:
        _emit_scoped_state_snapshot(campaign, game_session, state)

    return jsonify({"scene_stack": serialize_scene_stack(scene_stack)}), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/transition", methods=["POST"])
@limiter.limit("60 per hour")
@jwt_required()
def play_transition_session(campaign_id, session_id):
    """Transition session lifecycle state with RBAC and readiness checks."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    target_state = str(data.get("target_state", "")).strip().lower()
    if target_state not in {"scheduled", "ready", "in_progress", "paused", "ended"}:
        return jsonify({"error": "invalid target_state"}), 400

    current_state = normalize_session_status(game_session.status)
    if target_state == current_state:
        state = ensure_session_state(campaign, game_session)
        return jsonify(
            {
                "session": _serialize_session_runtime(game_session),
                "state": state.serialize(),
                "mode": play_mode_from_session_status(game_session.status),
                "read_only": is_read_only_mode(game_session.status, session_role),
            }
        ), 200

    allowed_targets = SESSION_TRANSITIONS.get(current_state, set())
    if target_state not in allowed_targets:
        return jsonify({"error": f"invalid transition: {current_state} -> {target_state}"}), 409

    state = ensure_session_state(campaign, game_session)
    if target_state == "in_progress":
        ready_report = run_ready_check(campaign, game_session, session_role)
        if ready_report["blocking_issues"]:
            return jsonify({"error": "ready-check blocked start", "ready_check": ready_report}), 409
        if not data.get("ignore_warnings", False) and ready_report["warnings"]:
            return jsonify({"error": "ready-check warnings require confirmation", "ready_check": ready_report}), 409

    previous_state = current_state
    game_session.status = target_state
    if target_state == "in_progress" and not game_session.started_at:
        game_session.started_at = utcnow()
    if target_state == "ended":
        game_session.ended_at = utcnow()

    state.state_status = state_status_from_session_status(target_state)
    state.bump_version()
    refresh_state_snapshot(state)

    if target_state == "in_progress":
        create_session_snapshot(game_session, state, "start", user.id)
    if target_state == "ended":
        create_session_snapshot(game_session, state, "end", user.id)

    db.session.commit()
    increment_counter("play_transitions_total")
    increment_labeled_counter("play_transitions_by_target", target_state)

    room = _room_name(campaign.id, game_session.id)
    transition_payload = build_event_envelope(campaign.id, game_session.id, {
        "campaign_id": campaign.id,
        "session_id": game_session.id,
        "previous_state": previous_state,
        "target_state": target_state,
        "state_version": state.version,
        "changed_by": user.id,
    })
    socketio.emit("session:state_changed", transition_payload, room=room)
    socketio.emit(
        "play:mode",
        build_event_envelope(campaign.id, game_session.id, {
            "campaign_id": campaign.id,
            "session_id": game_session.id,
            "mode": play_mode_from_session_status(target_state),
            "status": target_state,
        }),
        room=room,
    )
    _emit_scoped_state_snapshot(campaign, game_session, state)

    return jsonify(
        {
            "session": _serialize_session_runtime(game_session),
            "state": state.serialize(),
            "mode": play_mode_from_session_status(game_session.status),
            "read_only": is_read_only_mode(game_session.status, session_role),
        }
    ), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/actions/execute", methods=["POST"])
@limiter.limit("240 per hour")
@jwt_required()
def play_execute_action(campaign_id, session_id):
    """Execute action-bar action with server-side permission checks."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role

    mode = play_mode_from_session_status(game_session.status)
    if mode != "live":
        return jsonify({"error": "actions are only available during live session"}), 409
    if is_read_only_mode(game_session.status, session_role):
        return jsonify({"error": "read_only mode"}), 403

    data = request.get_json() or {}
    token_id, parse_error = coerce_int(data.get("token_id"), "token_id")
    if parse_error:
        return parse_error
    action_code = str(data.get("action_code", "")).strip().lower()
    if not action_code:
        return jsonify({"error": "action_code required"}), 400

    target_token_id = data.get("target_token_id")
    if target_token_id is not None:
        target_token_id, parse_error = coerce_int(target_token_id, "target_token_id")
        if parse_error:
            return parse_error

    token = TokenState.query.filter_by(id=token_id, game_session_id=game_session.id).first()
    if not token or token.deleted_at is not None:
        return jsonify({"error": "token not found"}), 404

    is_operator = is_operator_role(session_role)
    if not is_operator and token.owner_user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    result, action_error = execute_action(
        action_code=action_code,
        token_id=token.id,
        actor_user_id=user.id,
        target_token_id=target_token_id,
        payload=data.get("payload") if isinstance(data.get("payload"), dict) else {},
    )
    if action_error:
        return jsonify({"error": action_error["message"]}), 400

    room = _room_name(campaign.id, game_session.id)
    socketio.emit(
        "action:executed",
        build_event_envelope(campaign.id, game_session.id, {
            "campaign_id": campaign.id,
            "session_id": game_session.id,
            "result": result,
        }),
        room=room,
    )

    return jsonify({"result": result}), 200


# S09: loot transfer. Single source token per call (Apply decision: a
# multi-source atomic transfer was scoped out this slice -- real
# multi-source atomicity adds meaningful transaction complexity for a
# rarely-needed edge case; looting two corpses is two clicks, not a
# functional gap). CRITICAL per the research doc: idempotency-keyed so a
# network retry returns the cached result instead of re-executing, and
# every quantity decrement is a single conditional UPDATE checked by
# rowcount -- safe under concurrent access without needing an explicit
# row lock, and portable between SQLite (dev) and Postgres (prod).
@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/loot/transfer", methods=["POST"])
@limiter.limit("120 per hour")
@jwt_required()
def play_transfer_loot(campaign_id, session_id):
    """Transfer items from a loot-source token into a recipient character."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role

    mode = play_mode_from_session_status(game_session.status)
    if mode != "live":
        return jsonify({"error": "loot transfer is only available during live session"}), 409
    if is_read_only_mode(game_session.status, session_role):
        return jsonify({"error": "read_only mode"}), 403

    data = request.get_json() or {}
    idempotency_key = str(data.get("idempotency_key", "")).strip()
    if not idempotency_key:
        return jsonify({"error": "idempotency_key required"}), 400

    existing = LootTransfer.query.filter_by(idempotency_key=idempotency_key).first()
    if existing:
        # A retried request (e.g. after a network timeout) must never
        # re-execute -- return the already-committed result.
        return jsonify({"transfer": existing.serialize(), "cached": True}), 200

    source_token_id, error = coerce_int(data.get("source_token_id"), "source_token_id")
    if error:
        return error
    recipient_character_id, error = coerce_int(data.get("recipient_character_id"), "recipient_character_id")
    if error:
        return error

    items = data.get("items")
    if not isinstance(items, list) or not items:
        return jsonify({"error": "items must be a non-empty list"}), 400

    source_token = TokenState.query.filter_by(
        id=source_token_id, game_session_id=game_session.id, deleted_at=None
    ).first()
    if not source_token:
        return jsonify({"error": "source token not found"}), 404
    if not source_token.is_loot_source:
        return jsonify({"error": "token is not a loot source"}), 400
    # S09 Apply decision: a loot-source token (corpse/chest) is inherently
    # shared/table-wide by design -- any active session member may loot
    # from one, unlike the owner-or-DM model every other token mutation in
    # this app uses. There is no per-token "restrict to certain players"
    # flag in the data model; that is out of scope for this slice.

    recipient = Character.query.get(recipient_character_id)
    if not recipient or recipient.campaign_id != campaign.id:
        return jsonify({"error": "recipient character not found"}), 404
    is_operator = is_operator_role(session_role)
    if not (recipient.user_id == user.id or recipient.is_party_stash or is_operator):
        return jsonify({"error": "forbidden"}), 403

    transferred_summary = []
    for item_request in items:
        token_loot_id, error = coerce_int((item_request or {}).get("token_loot_id"), "token_loot_id")
        if error:
            return error
        quantity, error = coerce_int((item_request or {}).get("quantity"), "quantity")
        if error:
            return error
        if quantity <= 0:
            return jsonify({"error": "quantity must be positive"}), 400

        loot_row = TokenLoot.query.filter_by(id=token_loot_id, token_id=source_token.id).first()
        if not loot_row:
            db.session.rollback()
            return jsonify({"error": f"item {token_loot_id} not found on source token"}), 404

        update_result = db.session.execute(
            db.text("UPDATE token_loot SET quantity = quantity - :qty WHERE id = :id AND quantity >= :qty"),
            {"qty": quantity, "id": loot_row.id},
        )
        if update_result.rowcount == 0:
            db.session.rollback()
            return jsonify({"error": f"not enough {loot_row.name} remaining on the source"}), 409

        db.session.refresh(loot_row)
        if loot_row.quantity <= 0:
            db.session.delete(loot_row)

        # Stack onto an existing matching item on the recipient, or create
        # a new one -- "5x + 3x already held = 8x", never two entries.
        existing_item = InventoryItem.query.filter_by(
            character_id=recipient.id, name=loot_row.name
        ).first()
        if existing_item:
            existing_item.quantity = (existing_item.quantity or 0) + quantity
        else:
            db.session.add(InventoryItem(
                character_id=recipient.id,
                name=loot_row.name,
                item_type=loot_row.item_type,
                quantity=quantity,
                weight_per_unit=loot_row.weight_per_unit,
                cost=loot_row.cost,
                is_consumable=loot_row.is_consumable,
                # S09 Apply decision: cursed items transfer freely, no
                # special-case blocking/DM-approval logic this slice.
                is_cursed=loot_row.is_cursed,
                description=loot_row.description,
                effects=loot_row.effects,
            ))
        transferred_summary.append({"name": loot_row.name, "quantity": quantity})

    transfer = LootTransfer(
        idempotency_key=idempotency_key,
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        actor_user_id=user.id,
        source_token_id=source_token.id,
        recipient_character_id=recipient.id,
        items_transferred=transferred_summary,
    )
    db.session.add(transfer)

    # Audit (Apply decision: both session chat AND this loot_transfers row
    # serve as the audit trail -- already the drafted contract, no extra
    # surface to build or keep in sync).
    items_text = ", ".join(f"{entry['quantity']}x {entry['name']}" for entry in transferred_summary)
    chat_message = ChatMessage(
        campaign_id=campaign.id,
        game_session_id=game_session.id,
        author_user_id=user.id,
        content=f"überträgt {items_text} von {source_token.name} an {recipient.name}.",
        content_type="loot_transfer",
    )
    db.session.add(chat_message)
    db.session.commit()

    room = _room_name(campaign.id, game_session.id)
    # The audit row is written above, but writing it alone only surfaces on
    # the NEXT bootstrap/reload -- connected clients' chat logs only ever
    # append on receiving a "chat:message_sent" broadcast (same rule the
    # regular chat:message_sent socket handler and _handleChatBroadcast
    # both rely on), which loot:transferred alone does not trigger. Caught
    # by the loot_transfer robot flow: the chat panel stayed on "Noch keine
    # Chat-Nachrichten" through a completed transfer.
    socketio.emit(
        "chat:message_sent",
        build_event_envelope(campaign.id, game_session.id, {
            "message_id": chat_message.id,
            "message": chat_message.content,
            "sender_id": user.id,
            "sender_name": user.username,
            "timestamp": chat_message.created_at.isoformat() if chat_message.created_at else utcnow().isoformat(),
        }),
        room=room,
    )
    socketio.emit(
        "loot:transferred",
        build_event_envelope(campaign.id, game_session.id, {
            "transfer": transfer.serialize(),
            "source_token_id": source_token.id,
            "message_id": chat_message.id,
        }),
        room=room,
    )

    return jsonify({"transfer": transfer.serialize()}), 201


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/loot/<int:token_id>", methods=["GET"])
@jwt_required()
def play_get_token_loot(campaign_id, session_id, token_id):
    """List items currently on a loot-source token, and eligible recipient
    characters for the requesting user (their own characters in this
    campaign, plus any party-stash characters)."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role

    token = TokenState.query.filter_by(
        id=token_id, game_session_id=game_session.id, deleted_at=None
    ).first()
    if not token:
        return jsonify({"error": "token not found"}), 404
    if not token.is_loot_source:
        return jsonify({"error": "token is not a loot source"}), 400

    items = TokenLoot.query.filter_by(token_id=token.id).filter(TokenLoot.quantity > 0).all()

    is_operator = is_operator_role(session_role)
    recipient_query = Character.query.filter_by(campaign_id=campaign.id, deleted_at=None)
    if is_operator:
        recipients = recipient_query.all()
    else:
        recipients = recipient_query.filter(
            db.or_(Character.user_id == user.id, Character.is_party_stash.is_(True))
        ).all()

    return jsonify({
        "token": {"id": token.id, "name": token.name},
        "items": [item.serialize() for item in items],
        "recipients": [r.serialize() for r in recipients],
    }), 200


@play_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/loot/<int:token_id>/items", methods=["POST"])
@limiter.limit("120 per hour")
@jwt_required()
def play_add_token_loot_item(campaign_id, session_id, token_id):
    """DM stocks a loot-source token with an item -- without this there is
    no way to ever populate a corpse/chest, so the whole transfer feature
    would be unreachable end to end. Minimal by design: name + quantity
    only, matching TokenLoot's own required fields; richer authoring (item
    templates, a shared catalog) is out of scope for this slice."""
    user, campaign, game_session, session_role = _get_context(campaign_id, session_id)
    if isinstance(session_role, tuple):
        return session_role
    if not is_operator_role(session_role):
        return jsonify({"error": "forbidden"}), 403

    token = TokenState.query.filter_by(
        id=token_id, game_session_id=game_session.id, deleted_at=None
    ).first()
    if not token:
        return jsonify({"error": "token not found"}), 404

    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    quantity, error = coerce_int(data.get("quantity", 1), "quantity")
    if error:
        return error
    if quantity <= 0:
        return jsonify({"error": "quantity must be positive"}), 400

    if not token.is_loot_source:
        token.is_loot_source = True

    loot_item = TokenLoot(
        token_id=token.id,
        name=name,
        item_type=str(data.get("item_type") or "").strip() or None,
        quantity=quantity,
        weight_per_unit=data.get("weight_per_unit"),
        cost=str(data.get("cost") or "").strip() or None,
        is_consumable=bool(data.get("is_consumable")),
        is_cursed=bool(data.get("is_cursed")),
        description=str(data.get("description") or "").strip() or None,
    )
    db.session.add(loot_item)
    db.session.commit()

    room = _room_name(campaign.id, game_session.id)
    socketio.emit(
        "loot:updated",
        build_event_envelope(campaign.id, game_session.id, {
            "token_id": token.id,
            "item": loot_item.serialize(),
        }),
        room=room,
    )

    return jsonify({"item": loot_item.serialize(), "token": {"id": token.id, "is_loot_source": token.is_loot_source}}), 201
