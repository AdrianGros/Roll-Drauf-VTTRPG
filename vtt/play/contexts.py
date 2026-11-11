"""One authorization boundary for HTTP, socket events and outbound audiences.

Capabilities are never accepted as user identity: the independently authenticated
user and current membership must agree on every use.
"""

from datetime import timedelta
from functools import wraps
from hashlib import sha256
import re
import secrets

from flask import g, has_request_context, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from vtt.extensions import db
from vtt.models import Campaign, GameSession, User
from vtt.models.table_context import TableContext
from vtt.utils.time import utcnow

SESSION_PATH = re.compile(r"^/api/(?:play/)?campaigns/(\d+)/sessions/(\d+)(?:/|$)")
ROOM_PATH = re.compile(r"^campaign:(\d+):session:(\d+)(?::|$)")
LEGACY_PATH = re.compile(r"^/api/sessions/(\d+)(?:/|$)")
MOD_ROOM = re.compile(r"^campaign:(\d+):mods$")


def digest(value):
    return sha256(str(value or "").encode()).hexdigest()


def validate(context, user_id=None, campaign_id=None, session_id=None):
    if context is None or context.revoked_at or context.expires_at <= utcnow():
        return False
    from vtt.models import Session
    login = Session.query.filter_by(token_jti=context.auth_jti).first()
    if login and login.revoked_at is not None:
        return False
    try:
        if user_id is not None and context.user_id != int(user_id):
            return False
        if campaign_id is not None and context.campaign_id != int(campaign_id):
            return False
        if session_id is not None and context.game_session_id != int(session_id):
            return False
    except (ValueError, TypeError):
        return False
    user = db.session.get(User, context.user_id, populate_existing=True)
    campaign = db.session.get(Campaign, context.campaign_id, populate_existing=True)
    session = db.session.get(GameSession, context.game_session_id)
    if not user or not user.is_usable() or not campaign or not campaign.is_public():
        return False
    if not session or session.campaign_id != campaign.id:
        return False
    from vtt.play.service import get_session_role, is_operator_role
    role = get_session_role(campaign, user.id)
    return bool(role) and (context.mode == "player" or
                          context.mode == "dm" and is_operator_role(role))


def resolve(token, tab, user_id, campaign_id=None, session_id=None):
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        return None
    if not isinstance(tab, str) or not 16 <= len(tab) <= 128:
        return None
    context = TableContext.query.filter_by(token_hash=digest(token), tab_hash=digest(tab)).first()
    return context if validate(context, user_id, campaign_id, session_id) else None


def current_role(campaign_id, user_id, session_id):
    if not has_request_context():
        return None
    context = getattr(g, "table_context", None)
    if not validate(context, user_id, campaign_id, session_id):
        return None
    from vtt.play.service import get_session_role
    campaign = db.session.get(Campaign, campaign_id)
    role = get_session_role(campaign, user_id)
    return "PLAYER" if context.mode == "player" and role != "OBSERVER" else role


def restrict_campaign_role(campaign_id, user_id):
    """A carried player capability must also lower campaign-side DM helpers."""
    context = getattr(g, "table_context", None) if has_request_context() else None
    return bool(context and context.user_id == user_id and
                (context.campaign_id != campaign_id or context.mode == "player"))


def issue(user_id, campaign_id, session_id, mode, tab):
    if mode not in {"player", "dm"} or not isinstance(tab, str) or not 16 <= len(tab) <= 128:
        return None, (jsonify(error="invalid_context_request"), 400)
    token = secrets.token_urlsafe(32)
    context = TableContext(token_hash=digest(token), tab_hash=digest(tab), auth_jti=get_jwt()["jti"], user_id=user_id,
                           campaign_id=campaign_id, game_session_id=session_id, mode=mode,
                           expires_at=utcnow() + timedelta(hours=8))
    if not validate(context, user_id, campaign_id, session_id):
        return None, (jsonify(error="context_forbidden"), 403)
    old = getattr(g, "table_context", None)
    if old and old.user_id == user_id and old.game_session_id == session_id:
        old.revoked_at = utcnow()
    db.session.add(context)
    db.session.commit()
    g.table_context = context
    return {"token": token, "tab": tab, "mode": mode,
            "expires_at": context.expires_at.isoformat() + "Z"}, None


def install_http_guard(app):
    @app.before_request
    def table_context_boundary():
        g.pop("table_context", None)
        # Authentication endpoints have their own access/refresh JWT contracts.
        # In particular a table header must not turn refresh into an access-JWT check.
        if request.path.startswith("/api/auth/"):
            return None
        match = SESSION_PATH.match(request.path)
        legacy = LEGACY_PATH.match(request.path)
        entry = bool(match and request.path.endswith("/contexts"))
        token = request.headers.get("X-VTT-Context")
        if entry or (not match and not legacy and not token) or request.method == "OPTIONS":
            return None
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        legacy_session = db.session.get(GameSession, int(legacy[1])) if legacy else None
        context = resolve(token, request.headers.get("X-VTT-Tab"), user_id,
                          int(match[1]) if match else legacy_session.campaign_id if legacy_session else None,
                          int(match[2]) if match else int(legacy[1]) if legacy else None)
        if context is None or legacy and context.mode != "dm":
            return jsonify(error="table_context_required",
                           message="Bitte tritt diesem Tisch erneut ausdrücklich als Spieler oder DM bei."), 403
        resource_campaign = (request.view_args or {}).get("campaign_id")
        if resource_campaign is not None and context.campaign_id != resource_campaign:
            return jsonify(error="context_resource_mismatch"), 403
        g.table_context = context
        return None


def install_socket_guard(socketio):
    """Wrap registered event entries and prune revoked recipients before send.

    Installed on the current server instance, never the global SocketIO object,
    so repeated app factories in tests cannot stack wrappers.
    """
    server = socketio.server
    bindings = {}
    server.table_context_bindings = bindings

    def evict(sid):
        bindings.pop(sid, None)
        for room in list(server.rooms(sid, namespace="/") or []):
            if ROOM_PATH.match(str(room)) or MOD_ROOM.match(str(room)):
                server.leave_room(sid, room, namespace="/")
        from vtt.socket_handlers import _connected_rooms, _room_presence
        _connected_rooms[sid] = {room for room in _connected_rooms.get(sid, set())
                                 if not ROOM_PATH.match(room) and not MOD_ROOM.match(room)}
        for presence in _room_presence.values():
            presence.pop(sid, None)

    original_emit = server.emit

    def guarded_emit(event, data=None, to=None, room=None, **kwargs):
        audience = to or room
        if isinstance(audience, str) and (ROOM_PATH.match(audience) or MOD_ROOM.match(audience)):
            participants = list(server.manager.get_participants("/", audience))
            for sid, _ in participants:
                context_id = bindings.get(sid)
                context = db.session.get(TableContext, context_id, populate_existing=True) if context_id else None
                valid = validate(context)
                if MOD_ROOM.match(audience):
                    if context:
                        valid = valid and context.mode == "dm"
                    elif sid not in bindings:
                        from vtt.socket_handlers import _connected_users, _is_admin
                        user_id = _connected_users.get(sid)
                        user = db.session.get(User, user_id) if user_id else None
                        campaign_id = int(MOD_ROOM.match(audience)[1])
                        # An independent moderation surface still revalidates
                        # account and campaign rights on delivery.
                        from vtt.play.service import get_session_role, is_operator_role
                        campaign = db.session.get(Campaign, campaign_id)
                        valid = bool(user and user.is_usable() and campaign and
                                     (_is_admin(user) or is_operator_role(get_session_role(campaign, user.id))))
                if not valid:
                    evict(sid)
                    original_emit("table:context_revoked", {"reason": "context_expired_or_revoked"}, to=sid)
        return original_emit(event, data, to=to, room=room, **kwargs)

    server.emit = guarded_emit

    def decorate(event, handler):
        @wraps(handler)
        def guarded(*args):
            if event == "disconnect":
                context_id = bindings.get(request.sid)
                context = db.session.get(TableContext, context_id) if context_id else None
                if context and context.socket_sid == request.sid:
                    context.socket_sid = None
                    db.session.commit()
                bindings.pop(request.sid, None)
                return handler(*args)
            if event == "connect":
                return handler(*args)
            from vtt.socket_handlers import _parse_authenticated_user
            user, error = _parse_authenticated_user()
            if error:
                evict(request.sid)
                return {"error": "unauthorized"}
            payload = args[0] if args and isinstance(args[0], dict) else {}
            if event == "session:join":
                context = resolve(payload.get("context_token"), payload.get("tab_id"), user.id,
                                  payload.get("campaign_id"), payload.get("session_id"))
                if context and context.socket_sid and context.socket_sid != request.sid:
                    if server.manager.is_connected(context.socket_sid, "/"):
                        context = None
                if context:
                    evict(request.sid)
                    claimed = TableContext.query.filter_by(id=context.id, socket_sid=context.socket_sid).update(
                        {"socket_sid": request.sid}, synchronize_session=False)
                    db.session.commit()
                    if claimed:
                        db.session.refresh(context)
                        bindings[request.sid] = context.id
                    else:
                        context = None
            else:
                context_id = bindings.get(request.sid)
                context = db.session.get(TableContext, context_id, populate_existing=True) if context_id else None
                if not validate(context, user.id, payload.get("campaign_id"), payload.get("session_id")):
                    context = None
            if event.startswith("mod:") and context is None and request.sid not in bindings:
                return handler(*args)  # separate moderator interface, not a table fallback
            if context is None or event.startswith("mod:") and context.mode != "dm":
                evict(request.sid)
                original_emit("table:context_revoked", {"reason": "table_context_required"}, to=request.sid)
                return {"error": "table_context_required"}
            g.table_context = context
            if event == "roll_dice":
                from vtt.play.service import is_read_only_mode
                session = db.session.get(GameSession, context.game_session_id)
                if is_read_only_mode(session.status, current_role(context.campaign_id, user.id, session.id)):
                    return {"error": "read_only"}
            return handler(*args)
        return guarded

    for event, handler in list(server.handlers.get("/", {}).items()):
        # Flask's wrapper must establish request.sid/app/g before our guard.
        socketio.on_event(event, decorate(event, getattr(handler, "__wrapped__", handler)))
