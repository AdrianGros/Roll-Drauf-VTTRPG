"""Community chat, reporting, and moderation API routes."""

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from vtt_app.community import community_bp, policy, service
from vtt_app.extensions import db, limiter, socketio
from vtt_app.models import Campaign, ChatMessage, GameSession, ModerationAction, ModerationReport, User
from vtt_app.utils.time import utcnow


def _get_current_user():
    user_id = get_jwt_identity()
    if not user_id:
        return None, (jsonify({"error": "authentication required"}), 401)

    user = db.session.get(User, int(user_id))
    if not user or not user.is_active:
        return None, (jsonify({"error": "user not found"}), 404)
    return user, None


def _coerce_int(raw_value, field_name: str):
    try:
        return int(raw_value), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{field_name} must be a number"}), 400)


def _get_campaign_or_404(campaign_id: int):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or not campaign.is_public():
        return None, (jsonify({"error": "campaign not found"}), 404)
    return campaign, None


def _get_session_or_404(campaign_id: int, session_id: int):
    game_session = GameSession.query.filter_by(id=session_id, campaign_id=campaign_id).first()
    if not game_session:
        return None, (jsonify({"error": "session not found"}), 404)
    return game_session, None


def _require_active_member(campaign: Campaign, user: User):
    if not policy.is_active_member(campaign, user.id):
        return jsonify({"error": "forbidden"}), 403
    return None


def _emit_member_event(campaign_id: int, session_id: int, event_name: str, payload: dict):
    socketio.emit(event_name, payload, room=service.session_room_name(campaign_id, session_id))


def _emit_mod_event(campaign_id: int, event_name: str, payload: dict):
    socketio.emit(event_name, payload, room=service.mod_room_name(campaign_id))


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages", methods=["GET"])
@jwt_required()
def list_chat_messages(campaign_id, session_id):
    """List paginated chat messages for an active campaign member."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    game_session, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error
    membership_error = _require_active_member(campaign, user)
    if membership_error:
        return membership_error

    limit = service.normalize_limit(request.args.get("limit"), default=50, max_value=200)
    before_id = service.normalize_before_id(request.args.get("before_id"))

    query = ChatMessage.query.filter_by(campaign_id=campaign.id, game_session_id=game_session.id).order_by(ChatMessage.id.desc())
    if before_id:
        query = query.filter(ChatMessage.id < before_id)

    rows_desc = query.limit(limit).all()
    rows = list(reversed(rows_desc))
    viewer_is_mod = policy.can_moderate_campaign(campaign, user)

    next_before_id = rows_desc[-1].id if rows_desc else None
    return jsonify(
        {
            "messages": [service.message_for_viewer(message, user.id, viewer_is_mod) for message in rows],
            "next_before_id": next_before_id,
        }
    ), 200


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def create_chat_message(campaign_id, session_id):
    """Create a chat message if the user is not muted/banned."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    game_session, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error
    membership_error = _require_active_member(campaign, user)
    if membership_error:
        return membership_error

    service.deactivate_expired_actions()

    active_bans = service.active_sanctions(campaign.id, user.id, {"ban"})
    if active_bans:
        return jsonify({"error": "user is banned from this campaign"}), 403

    active_mutes = service.active_sanctions(campaign.id, user.id, {"mute"})
    if active_mutes:
        return jsonify({"error": "user is muted"}), 403

    data = request.get_json() or {}
    message, created, message_error = service.create_chat_message(
        campaign_id=campaign.id,
        session_id=game_session.id,
        author_user_id=user.id,
        content=data.get("content"),
        client_event_id=data.get("client_event_id"),
    )
    if message_error:
        return jsonify({"error": message_error}), 400

    db.session.commit()

    serialized = message.serialize()
    _emit_member_event(campaign.id, game_session.id, "chat:message_created", {"message": serialized})
    return jsonify({"message": serialized}), (201 if created else 200)


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages/<int:message_id>", methods=["PATCH"])
@limiter.limit("80 per hour")
@jwt_required()
def update_chat_message(campaign_id, session_id, message_id):
    """Update chat message content (owner window) or redact as moderator."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    game_session, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error

    message = ChatMessage.query.filter_by(id=message_id, campaign_id=campaign.id, game_session_id=game_session.id).first()
    if not message:
        return jsonify({"error": "message not found"}), 404

    is_member = policy.is_active_member(campaign, user.id)
    is_moderator = policy.can_moderate_campaign(campaign, user)
    if not is_member and not is_moderator:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    new_content = str(data.get("content", "")).strip()

    if service.can_edit_own_message(message, user.id):
        if not new_content:
            return jsonify({"error": "content required"}), 400
        if len(new_content) > 1000:
            return jsonify({"error": "content must be at most 1000 characters"}), 400
        message.content = new_content
        message.edited_at = utcnow()
    elif is_moderator:
        replacement = new_content or "[message redacted by moderation]"
        if len(replacement) > 1000:
            return jsonify({"error": "content must be at most 1000 characters"}), 400
        message.content = replacement
        message.edited_at = utcnow()
        if data.get("redact"):
            message.moderation_state = "hidden_moderation"
    else:
        return jsonify({"error": "forbidden"}), 403

    db.session.commit()
    serialized = message.serialize()
    _emit_member_event(campaign.id, game_session.id, "chat:message_updated", {"message": serialized})
    return jsonify({"message": serialized}), 200


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/chat/messages/<int:message_id>", methods=["DELETE"])
@limiter.limit("80 per hour")
@jwt_required()
def delete_chat_message(campaign_id, session_id, message_id):
    """Soft-delete chat message by owner (windowed) or moderator."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    game_session, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error

    message = ChatMessage.query.filter_by(id=message_id, campaign_id=campaign.id, game_session_id=game_session.id).first()
    if not message:
        return jsonify({"error": "message not found"}), 404

    is_member = policy.is_active_member(campaign, user.id)
    is_moderator = policy.can_moderate_campaign(campaign, user)
    if not is_member and not is_moderator:
        return jsonify({"error": "forbidden"}), 403

    if service.can_edit_own_message(message, user.id):
        service.soft_delete_message(message, user.id, moderation_state="hidden_author")
    elif is_moderator:
        service.soft_delete_message(message, user.id, moderation_state="hidden_moderation")
    else:
        return jsonify({"error": "forbidden"}), 403

    db.session.commit()
    _emit_member_event(
        campaign.id,
        game_session.id,
        "chat:message_deleted",
        {
            "message_id": message.id,
            "moderation_state": message.moderation_state,
            "deleted_at": message.deleted_at.isoformat() if message.deleted_at else None,
        },
    )
    return jsonify({"message": "deleted", "message_id": message.id}), 200


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/reports", methods=["POST"])
@limiter.limit("5 per hour")
@jwt_required()
def create_report(campaign_id, session_id):
    """Create a moderation report."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    game_session, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error
    membership_error = _require_active_member(campaign, user)
    if membership_error:
        return membership_error

    data = request.get_json() or {}
    target_user_id = data.get("target_user_id")
    if target_user_id is not None:
        target_user_id, error = _coerce_int(target_user_id, "target_user_id")
        if error:
            return error

    target_message_id = data.get("target_message_id")
    target_message = None
    if target_message_id is not None:
        target_message_id, error = _coerce_int(target_message_id, "target_message_id")
        if error:
            return error
        target_message = ChatMessage.query.filter_by(
            id=target_message_id,
            campaign_id=campaign.id,
            game_session_id=game_session.id,
        ).first()
        if not target_message:
            return jsonify({"error": "target message not found"}), 404
        if target_user_id is None:
            target_user_id = target_message.author_user_id

    report, report_error = service.create_report(
        campaign_id=campaign.id,
        session_id=game_session.id,
        reporter_user_id=user.id,
        reason_code=data.get("reason_code"),
        description=data.get("description"),
        target_user_id=target_user_id,
        target_message_id=target_message_id,
    )
    if report_error:
        return jsonify({"error": report_error}), 400

    db.session.commit()
    payload = {"report": report.serialize()}
    _emit_mod_event(campaign.id, "moderation:report_created", payload)
    return jsonify(payload), 201


@community_bp.route("/campaigns/<int:campaign_id>/reports", methods=["GET"])
@jwt_required()
def list_reports(campaign_id):
    """List campaign moderation reports for DM/Admin."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    limit = service.normalize_limit(request.args.get("limit"), default=50, max_value=200)
    cursor = service.normalize_before_id(request.args.get("cursor"))
    status_filter = str(request.args.get("status", "")).strip().lower()
    priority_filter = str(request.args.get("priority", "")).strip().lower()

    query = ModerationReport.query.filter_by(campaign_id=campaign.id).order_by(ModerationReport.id.desc())
    if cursor:
        query = query.filter(ModerationReport.id < cursor)
    if status_filter:
        if status_filter not in service.VALID_REPORT_STATUS:
            return jsonify({"error": "invalid status filter"}), 400
        query = query.filter_by(status=status_filter)
    if priority_filter:
        if priority_filter not in {"low", "medium", "high"}:
            return jsonify({"error": "invalid priority filter"}), 400
        query = query.filter_by(priority=priority_filter)

    reports = query.limit(limit).all()
    next_cursor = reports[-1].id if reports else None
    return jsonify({"reports": [report.serialize() for report in reports], "next_cursor": next_cursor}), 200


@community_bp.route("/campaigns/<int:campaign_id>/reports/<int:report_id>/assign", methods=["POST"])
@limiter.limit("100 per hour")
@jwt_required()
def assign_report(campaign_id, report_id):
    """Assign moderation report to a moderator."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    report = ModerationReport.query.filter_by(id=report_id, campaign_id=campaign.id).first()
    if not report:
        return jsonify({"error": "report not found"}), 404

    data = request.get_json() or {}
    assigned_to_user_id, error = _coerce_int(data.get("assigned_to_user_id"), "assigned_to_user_id")
    if error:
        return error
    assignee = db.session.get(User, assigned_to_user_id)
    if not assignee or not assignee.is_active:
        return jsonify({"error": "assignee not found"}), 404

    report.assigned_to_user_id = assigned_to_user_id
    if report.status == "open":
        report.status = "in_review"

    db.session.commit()
    payload = {"report": report.serialize()}
    _emit_mod_event(campaign.id, "moderation:report_updated", payload)
    return jsonify(payload), 200


@community_bp.route("/campaigns/<int:campaign_id>/reports/<int:report_id>/resolve", methods=["POST"])
@limiter.limit("100 per hour")
@jwt_required()
def resolve_report(campaign_id, report_id):
    """Resolve or reject a report."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    report = ModerationReport.query.filter_by(id=report_id, campaign_id=campaign.id).first()
    if not report:
        return jsonify({"error": "report not found"}), 404

    data = request.get_json() or {}
    resolution = str(data.get("resolution", "")).strip().lower()
    if resolution not in {"resolved", "rejected"}:
        return jsonify({"error": "resolution must be resolved or rejected"}), 400

    action_id = data.get("action_id")
    resolved_action_id = None
    if action_id is not None:
        resolved_action_id, error = _coerce_int(action_id, "action_id")
        if error:
            return error
        action = ModerationAction.query.filter_by(id=resolved_action_id, campaign_id=campaign.id).first()
        if not action:
            return jsonify({"error": "action not found"}), 404

    report.status = resolution
    report.resolution_note = str(data.get("resolution_note", "")).strip() or None
    report.resolved_action_id = resolved_action_id
    report.resolved_at = utcnow()

    db.session.commit()
    payload = {"report": report.serialize()}
    _emit_mod_event(campaign.id, "moderation:report_updated", payload)
    return jsonify(payload), 200


@community_bp.route("/campaigns/<int:campaign_id>/moderation/actions", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def create_moderation_action(campaign_id):
    """Apply a moderation action as DM/Admin (ban admin-only)."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    subject_user_id = data.get("subject_user_id")
    if subject_user_id is not None:
        subject_user_id, error = _coerce_int(subject_user_id, "subject_user_id")
        if error:
            return error

    subject_message = None
    subject_message_id = data.get("subject_message_id")
    if subject_message_id is not None:
        subject_message_id, error = _coerce_int(subject_message_id, "subject_message_id")
        if error:
            return error
        subject_message = ChatMessage.query.filter_by(id=subject_message_id, campaign_id=campaign.id).first()
        if not subject_message:
            return jsonify({"error": "subject message not found"}), 404

    source_report_id = data.get("source_report_id")
    if source_report_id is not None:
        source_report_id, error = _coerce_int(source_report_id, "source_report_id")
        if error:
            return error
        report = ModerationReport.query.filter_by(id=source_report_id, campaign_id=campaign.id).first()
        if not report:
            return jsonify({"error": "source report not found"}), 404

    duration_minutes = data.get("duration_minutes")
    if duration_minutes is not None:
        duration_minutes, error = _coerce_int(duration_minutes, "duration_minutes")
        if error:
            return error

    action, action_error = service.apply_moderation_action(
        campaign=campaign,
        actor=user,
        action_type=data.get("action_type"),
        reason=data.get("reason"),
        subject_user_id=subject_user_id,
        subject_message=subject_message,
        source_report_id=source_report_id,
        duration_minutes=duration_minutes,
    )
    if action_error:
        db.session.rollback()
        return jsonify({"error": action_error}), 400

    db.session.commit()

    action_payload = {"action": action.serialize(), "report_id": source_report_id}
    _emit_mod_event(campaign.id, "moderation:action_applied", action_payload)

    if action.subject_message and action.subject_message.game_session_id:
        _emit_member_event(
            campaign.id,
            action.subject_message.game_session_id,
            "chat:message_deleted",
            {
                "message_id": action.subject_message.id,
                "moderation_state": action.subject_message.moderation_state,
                "deleted_at": action.subject_message.deleted_at.isoformat() if action.subject_message.deleted_at else None,
            },
        )

    return jsonify(action_payload), 201


@community_bp.route("/campaigns/<int:campaign_id>/moderation/actions", methods=["GET"])
@jwt_required()
def list_moderation_actions(campaign_id):
    """List moderation actions for campaign moderators."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    query = ModerationAction.query.filter_by(campaign_id=campaign.id).order_by(ModerationAction.id.desc())
    active_raw = request.args.get("active")
    if active_raw is not None:
        active_normalized = str(active_raw).strip().lower()
        if active_normalized in {"true", "1", "yes"}:
            query = query.filter_by(is_active=True)
        elif active_normalized in {"false", "0", "no"}:
            query = query.filter_by(is_active=False)
        else:
            return jsonify({"error": "active must be boolean"}), 400

    subject_user_id = request.args.get("subject_user_id")
    if subject_user_id is not None:
        subject_user_id, error = _coerce_int(subject_user_id, "subject_user_id")
        if error:
            return error
        query = query.filter_by(subject_user_id=subject_user_id)

    limit = service.normalize_limit(request.args.get("limit"), default=100, max_value=200)
    actions = query.limit(limit).all()
    return jsonify({"actions": [action.serialize() for action in actions]}), 200


@community_bp.route("/campaigns/<int:campaign_id>/moderation/actions/<int:action_id>/revoke", methods=["POST"])
@limiter.limit("60 per hour")
@jwt_required()
def revoke_moderation_action(campaign_id, action_id):
    """Revoke an active moderation action."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    if not policy.can_moderate_campaign(campaign, user):
        return jsonify({"error": "forbidden"}), 403

    action = ModerationAction.query.filter_by(id=action_id, campaign_id=campaign.id).first()
    if not action:
        return jsonify({"error": "action not found"}), 404
    if not action.is_active:
        return jsonify({"error": "action already inactive"}), 409

    if action.action_type == "ban" and not policy.is_admin(user):
        return jsonify({"error": "ban revocation requires admin role"}), 403

    service.revoke_action(action, user.id)
    db.session.commit()

    payload = {
        "action_id": action.id,
        "revoked_at": action.revoked_at.isoformat() if action.revoked_at else None,
        "action": action.serialize(),
    }
    _emit_mod_event(campaign.id, "moderation:action_revoked", payload)
    return jsonify(payload), 200


@community_bp.route("/campaigns/<int:campaign_id>/sessions/<int:session_id>/voice/config", methods=["GET"])
@jwt_required()
def get_voice_config(campaign_id, session_id):
    """Return voice feature-flag status for the session."""
    user, error = _get_current_user()
    if error:
        return error

    campaign, error = _get_campaign_or_404(campaign_id)
    if error:
        return error
    _, error = _get_session_or_404(campaign.id, session_id)
    if error:
        return error
    membership_error = _require_active_member(campaign, user)
    if membership_error:
        return membership_error

    voice_enabled = bool(current_app.config.get("VOICE_ENABLED", False))
    return jsonify(
        {
            "voice_enabled": voice_enabled,
            "provider": None,
            "room": service.session_room_name(campaign.id, session_id),
        }
    ), 200
