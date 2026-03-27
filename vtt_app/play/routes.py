"""Play runtime API routes."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from vtt_app.extensions import db, limiter, socketio
from vtt_app.models import SceneLayer, TokenState
from vtt_app.play import play_bp
from vtt_app.play.actions import execute_action, get_action_catalog
from vtt_app.utils.metrics import increment_counter, increment_labeled_counter
from vtt_app.utils.realtime import build_event_envelope
from vtt_app.utils.time import utcnow
from vtt_app.play.service import (
    SESSION_TRANSITIONS,
    activate_scene_layer,
    coerce_int,
    create_session_snapshot,
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
    run_ready_check,
    serialize_scene_stack,
    serialize_state_payload,
    state_status_from_session_status,
)


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
        "scene_stack": serialize_scene_stack(scene_stack),
        "state_payload": serialize_state_payload(game_session, state),
        "action_catalog": get_action_catalog(),
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
    socketio.emit(
        "state:snapshot",
        build_event_envelope(campaign.id, game_session.id, serialize_state_payload(game_session, state)),
        room=room,
    )

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
    socketio.emit(
        "state:snapshot",
        build_event_envelope(campaign.id, game_session.id, serialize_state_payload(game_session, state)),
        room=room,
    )

    return jsonify(
        {
            "scene_stack": serialize_scene_stack(scene_stack),
            "active_layer": layer.serialize(),
            "state": state.serialize(),
        }
    ), 200


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
    socketio.emit(
        "state:snapshot",
        build_event_envelope(campaign.id, game_session.id, serialize_state_payload(game_session, state)),
        room=room,
    )

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
