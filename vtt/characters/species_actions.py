"""Race actions of a pinned homebrew Species, declared at the live table.

A declaration is validated against the pinned action (object, weight, distance, movement), then written as one
table chat message (`content_type="species_action"`). The client's idempotency key becomes the message's
`client_event_id`; the existing unique (author, session, client_event_id) constraint makes a retry return the
first message instead of writing a second one. The VTT does not simulate the object; the DM adjudicates.
"""

import re

from sqlalchemy.exc import IntegrityError

from vtt.characters import sheet_link
from vtt.extensions import db, socketio
from vtt.models import Campaign, ChatMessage
from vtt.rules_content import species_profiles as profiles
from vtt.utils.realtime import build_event_envelope
from vtt.utils.time import utcnow

CONTENT_TYPE = "species_action"
_KEY = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class ActionError(Exception):
    def __init__(self, code, message, status=422, **extra):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra


def _existing(user, game_session, event_id):
    return ChatMessage.query.filter_by(author_user_id=user.id, game_session_id=game_session.id, client_event_id=event_id).first()


def _receipt(message, *, duplicate):
    return {"messageId": message.id, "sessionId": message.game_session_id, "content": message.content,
            "duplicate": duplicate, "createdAt": message.created_at.isoformat() if message.created_at else None}


def _retry_receipt(existing, expected_content):
    if existing.content != expected_content:
        raise ActionError("idempotency_conflict", "Diese idempotencyKey wurde bereits für eine andere Erklärung verwendet.", 409)
    return _receipt(existing, duplicate=True)


def _broadcast(message, user):
    from vtt.socket_handlers import _room_name

    payload = {
        "message_id": message.id, "message": message.content, "sender_id": user.id, "sender_name": user.username,
        "content_type": CONTENT_TYPE,
        "timestamp": message.created_at.isoformat() if message.created_at else utcnow().isoformat(),
    }
    envelope = build_event_envelope(message.campaign_id, message.game_session_id, payload, advance=True)
    socketio.emit("chat:message_sent", envelope, room=_room_name(message.campaign_id, message.game_session_id))


def declare(user, char, action_id, body):
    """Validate and log one use of `action_id` for `char` by `user` (owner or DM; the caller checks). Commits."""
    from vtt.socket_handlers import _is_active_member, _reject_read_only

    body = body if isinstance(body, dict) else {}
    pin = profiles.pinned(sheet_link.srd_block(char))
    action = profiles.find_action(pin, action_id)
    if action is None:
        raise ActionError("unknown_action", "Diese Spezies-Aktion gibt es auf dem Bogen nicht.", 404)
    key = body.get("idempotencyKey")
    if not isinstance(key, str) or not _KEY.match(key):
        raise ActionError("idempotency_key_required", "idempotencyKey: 8 bis 64 Zeichen aus Buchstaben, Ziffern, - und _.", 400)
    declaration, problems = profiles.check_declaration(action, body)
    if problems:
        raise ActionError("invalid_declaration", "Die Erklärung passt nicht zur Regel der Spezies.", 422, problems=problems)
    game_session = sheet_link.roll_target_session(char)
    campaign = db.session.get(Campaign, char.campaign_id) if char.campaign_id else None
    if game_session is None or campaign is None or not _is_active_member(campaign.id, user.id) \
            or _reject_read_only(campaign, game_session, user):
        raise ActionError("no_live_session", "Spezies-Aktionen werden in einer laufenden Sitzung der Kampagne erklärt.", 409)
    event_id = f"sa:{char.id}:{action['id']}:{key}"
    content = profiles.declaration_text(char.name, action, declaration)
    existing = _existing(user, game_session, event_id)
    if existing is not None:
        return _retry_receipt(existing, content)
    message = ChatMessage(
        campaign_id=campaign.id, game_session_id=game_session.id, author_user_id=user.id,
        content=content, content_type=CONTENT_TYPE,
        client_event_id=event_id, visibility="public",
    )
    db.session.add(message)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = _existing(user, game_session, event_id)
        if existing is None:
            raise
        return _retry_receipt(existing, content)
    try:
        _broadcast(message, user)
    except Exception:  # the declaration is already stored; the chat history shows it on the next load
        pass
    return _receipt(message, duplicate=False)
