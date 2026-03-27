"""Service helpers for community chat, reporting, and moderation flows."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from vtt_app.extensions import db
from vtt_app.models import (
    Campaign,
    CampaignMember,
    ChatMessage,
    ModerationAction,
    ModerationReport,
    User,
)
from vtt_app.community import policy
from vtt_app.utils.time import utcnow

VALID_REASON_CODES = {"spam", "abuse", "harassment", "other"}
VALID_REPORT_STATUS = {"open", "in_review", "resolved", "rejected"}
VALID_ACTION_TYPES = {"warn", "mute", "delete_message", "kick", "ban"}


def now_utc():
    return utcnow()


def mod_room_name(campaign_id: int) -> str:
    return f"campaign:{campaign_id}:mods"


def session_room_name(campaign_id: int, session_id: int) -> str:
    return f"campaign:{campaign_id}:session:{session_id}"


def normalize_limit(raw_value, default: int = 50, max_value: int = 200) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return min(parsed, max_value)


def normalize_before_id(raw_value) -> int | None:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def active_sanctions(campaign_id: int, subject_user_id: int, action_types: set[str]) -> list[ModerationAction]:
    now = now_utc()
    return (
        ModerationAction.query.filter_by(campaign_id=campaign_id, subject_user_id=subject_user_id, is_active=True)
        .filter(ModerationAction.action_type.in_(list(action_types)))
        .filter(ModerationAction.revoked_at.is_(None))
        .filter(or_(ModerationAction.ends_at.is_(None), ModerationAction.ends_at > now))
        .order_by(ModerationAction.created_at.desc())
        .all()
    )


def deactivate_expired_actions() -> None:
    now = now_utc()
    expired = (
        ModerationAction.query.filter_by(is_active=True)
        .filter(ModerationAction.ends_at.is_not(None))
        .filter(ModerationAction.ends_at <= now)
        .all()
    )
    for action in expired:
        action.is_active = False


def create_chat_message(
    campaign_id: int,
    session_id: int,
    author_user_id: int,
    content: str,
    client_event_id: str | None = None,
) -> tuple[ChatMessage | None, bool, str | None]:
    normalized = str(content or "").strip()
    if not normalized:
        return None, False, "content required"
    if len(normalized) > 1000:
        return None, False, "content must be at most 1000 characters"

    normalized_event_id = str(client_event_id or "").strip() or None
    if normalized_event_id:
        existing = ChatMessage.query.filter_by(
            author_user_id=author_user_id,
            game_session_id=session_id,
            client_event_id=normalized_event_id,
        ).first()
        if existing:
            return existing, False, None

    message = ChatMessage(
        campaign_id=campaign_id,
        game_session_id=session_id,
        author_user_id=author_user_id,
        content=normalized,
        client_event_id=normalized_event_id,
        content_type="user",
        moderation_state="visible",
    )
    db.session.add(message)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        if normalized_event_id:
            existing = ChatMessage.query.filter_by(
                author_user_id=author_user_id,
                game_session_id=session_id,
                client_event_id=normalized_event_id,
            ).first()
            if existing:
                return existing, False, None
        return None, False, "message could not be created"

    return message, True, None


def can_edit_own_message(message: ChatMessage, user_id: int, window_minutes: int = 5) -> bool:
    if message.author_user_id != user_id:
        return False
    if message.deleted_at:
        return False
    return (now_utc() - message.created_at) <= timedelta(minutes=window_minutes)


def soft_delete_message(message: ChatMessage, actor_user_id: int, moderation_state: str = "hidden_moderation") -> None:
    message.deleted_at = now_utc()
    message.deleted_by = actor_user_id
    message.moderation_state = moderation_state
    message.edited_at = now_utc()


def create_report(
    campaign_id: int,
    session_id: int,
    reporter_user_id: int,
    reason_code: str,
    description: str | None = None,
    target_user_id: int | None = None,
    target_message_id: int | None = None,
) -> tuple[ModerationReport | None, str | None]:
    normalized_reason = str(reason_code or "").strip().lower()
    if normalized_reason not in VALID_REASON_CODES:
        return None, "invalid reason_code"

    if target_user_id is None and target_message_id is None:
        return None, "target_user_id or target_message_id required"

    report = ModerationReport(
        campaign_id=campaign_id,
        game_session_id=session_id,
        reporter_user_id=reporter_user_id,
        target_user_id=target_user_id,
        target_message_id=target_message_id,
        reason_code=normalized_reason,
        description=str(description or "").strip() or None,
        status="open",
        priority="medium",
    )
    db.session.add(report)
    db.session.flush()
    return report, None


def apply_moderation_action(
    campaign: Campaign,
    actor: User,
    action_type: str,
    reason: str | None = None,
    subject_user_id: int | None = None,
    subject_message: ChatMessage | None = None,
    source_report_id: int | None = None,
    duration_minutes: int | None = None,
) -> tuple[ModerationAction | None, str | None]:
    normalized_type = str(action_type or "").strip().lower()
    if normalized_type not in VALID_ACTION_TYPES:
        return None, "invalid action_type"

    if normalized_type == "ban" and not policy.can_apply_ban(actor):
        return None, "ban requires admin role"

    if normalized_type in {"warn", "mute", "kick", "ban"} and not subject_user_id:
        return None, "subject_user_id required"

    if normalized_type == "delete_message" and not subject_message:
        return None, "subject_message_id required"

    subject_user = None
    if subject_user_id:
        subject_user = db.session.get(User, subject_user_id)
        if not subject_user or not subject_user.is_active:
            return None, "subject user not found"
        if normalized_type in {"kick", "ban"} and subject_user_id == campaign.owner_id:
            return None, "campaign owner cannot be kicked or banned"

    now = now_utc()
    ends_at = None
    if normalized_type == "mute":
        minutes = duration_minutes if duration_minutes is not None else 30
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            return None, "duration_minutes must be a number"
        if minutes <= 0 or minutes > 10080:
            return None, "duration_minutes must be between 1 and 10080"
        ends_at = now + timedelta(minutes=minutes)

    action = ModerationAction(
        campaign_id=campaign.id,
        game_session_id=subject_message.game_session_id if subject_message else None,
        action_type=normalized_type,
        actor_user_id=actor.id,
        subject_user_id=subject_user_id,
        subject_message_id=subject_message.id if subject_message else None,
        source_report_id=source_report_id,
        reason=str(reason or "").strip() or None,
        starts_at=now,
        ends_at=ends_at,
        is_active=True,
    )
    db.session.add(action)
    db.session.flush()

    if normalized_type == "delete_message" and subject_message:
        soft_delete_message(subject_message, actor.id, moderation_state="hidden_moderation")

    if normalized_type in {"kick", "ban"} and subject_user_id:
        member = CampaignMember.query.filter_by(
            campaign_id=campaign.id,
            user_id=subject_user_id,
            status="active",
        ).first()
        if member:
            member.status = "kicked"

    return action, None


def revoke_action(action: ModerationAction, actor_user_id: int) -> None:
    action.is_active = False
    action.revoked_at = now_utc()
    action.revoked_by_user_id = actor_user_id


def message_for_viewer(message: ChatMessage, viewer_user_id: int, viewer_is_moderator: bool) -> dict:
    payload = message.serialize()
    if message.deleted_at and not viewer_is_moderator:
        payload["content"] = "[message removed]"
    return payload
