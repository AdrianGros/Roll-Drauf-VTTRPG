"""Persistent campaign text rooms. Membership is rechecked on every poll/write."""
from uuid import UUID
from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from vtt.conversations import actor, member, ConversationError
from vtt.community import service
from vtt.extensions import db, limiter
from vtt.models import Campaign, CampaignMember
from vtt.models.session_feedback import CampaignChatMessage

campaign_rooms_bp = Blueprint("campaign_rooms", __name__, url_prefix="/api/campaign-rooms")


@campaign_rooms_bp.errorhandler(ConversationError)
def denied(error):
    db.session.rollback()
    return jsonify(error=error.message), error.status


@campaign_rooms_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def room(user, campaign_id):
    campaign = db.session.get(Campaign, campaign_id, populate_existing=True)
    context = getattr(g, "table_context", None)
    if not campaign or not member(campaign, user.id) or (context and context.campaign_id != campaign.id):
        return None
    return campaign


@campaign_rooms_bp.get("")
@jwt_required()
def list_rooms():
    user = actor()
    ids = db.session.query(CampaignMember.campaign_id).filter_by(user_id=user.id, status="active")
    campaigns = Campaign.query.filter((Campaign.owner_id == user.id) | Campaign.id.in_(ids)).filter(Campaign.deleted_at.is_(None))
    return jsonify(rooms=[dict(id=c.id, name=c.name) for c in campaigns.order_by(Campaign.name) if member(c, user.id)])


@campaign_rooms_bp.route("/<int:campaign_id>", methods=["GET", "POST"])
@jwt_required()
@limiter.limit("120 per minute")
def messages(campaign_id):
    user = actor()
    campaign = room(user, campaign_id)
    if not campaign:
        return jsonify(error="not_found"), 404
    bans = service.active_sanctions(campaign.id, user.id, {"ban"})
    if bans:
        return jsonify(error="forbidden"), 403
    if request.method == "GET":
        query = CampaignChatMessage.query.filter_by(campaign_id=campaign.id)
        try:
            before, after = int(request.args.get("before", 0)), int(request.args.get("after", 0))
        except (ValueError, TypeError):
            return jsonify(error="invalid_cursor"), 400
        if before:
            query = query.filter(CampaignChatMessage.id < before)
        if after:
            query = query.filter(CampaignChatMessage.id > after)
            rows = query.order_by(CampaignChatMessage.id).limit(101).all()
        else:
            rows = list(reversed(query.order_by(CampaignChatMessage.id.desc()).limit(101).all()))
        more = len(rows) > 100
        rows = rows[:100] if after else rows[-100:]
        return jsonify(conversation=dict(campaign_id=campaign.id, campaign_name=campaign.name,
                                         partner_name="Kampagnenchat", self_user_id=user.id, can_send=True),
                       messages=[r.serialize() for r in rows], more=more)
    context = getattr(g, "table_context", None)
    if context:
        from vtt.play.contexts import current_role
        if current_role(campaign.id, user.id, context.game_session_id) not in {"DM", "CO_DM", "PLAYER"}:
            return jsonify(error="forbidden"), 403
    if service.active_sanctions(campaign.id, user.id, {"mute"}):
        return jsonify(error="muted"), 403
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify(error="invalid_body"), 400
    content = body.get("content")
    try:
        event_id = str(UUID(body.get("client_event_id", "")))
    except (ValueError, TypeError, AttributeError):
        return jsonify(error="invalid_event_id"), 400
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 2000:
        return jsonify(error="invalid_content"), 400
    existing = CampaignChatMessage.query.filter_by(campaign_id=campaign.id, author_user_id=user.id, client_event_id=event_id).first()
    if existing:
        if existing.content != content.strip():
            return jsonify(error="event_id_reused"), 409
        return jsonify(message=existing.serialize()), 200
    row = CampaignChatMessage(campaign_id=campaign.id, author_user_id=user.id,
                              client_event_id=event_id, content=content.strip())
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        row = CampaignChatMessage.query.filter_by(campaign_id=campaign.id, author_user_id=user.id, client_event_id=event_id).first()
        if row is None or row.content != content.strip():
            return jsonify(error="event_conflict"), 409
    return jsonify(message=row.serialize()), 201


@campaign_rooms_bp.get('/<int:campaign_id>/history')
@jwt_required()
@limiter.limit('120 per minute')
def previous_session_messages(campaign_id):
    """Public legacy history only; personal conversations never inherit DM authority."""
    from vtt.models import ChatMessage, GameSession
    user = actor()
    campaign = room(user, campaign_id)
    if not campaign:
        return jsonify(error='not_found'), 404
    if service.active_sanctions(campaign.id, user.id, {'ban'}):
        return jsonify(error='forbidden'), 403
    try:
        before = int(request.args.get('before', 0))
        if before < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify(error='invalid_cursor'), 400
    query = ChatMessage.query.join(GameSession, ChatMessage.game_session_id == GameSession.id).filter(
        ChatMessage.campaign_id == campaign.id, GameSession.campaign_id == campaign.id,
        ChatMessage.visibility == 'public', ChatMessage.moderation_state == 'visible',
        ChatMessage.deleted_at.is_(None))
    if before:
        query = query.filter(ChatMessage.id < before)
    rows = query.order_by(ChatMessage.id.desc()).limit(51).all()
    more = len(rows) > 50
    page = rows[:50]
    return jsonify(messages=[dict(id=r.id, source='session', source_key=f'session:{r.id}',
        session_id=r.game_session_id, session_name=r.game_session.name,
        author_name=r.author.username if r.author else 'Player', content=r.content,
        content_type=r.content_type, created_at=r.created_at.isoformat() if r.created_at else None)
        for r in reversed(page)], more=more, next_before=page[-1].id if more and page else None)
