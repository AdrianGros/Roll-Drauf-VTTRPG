"""Authenticated private conversations: participant + current membership on every call.

No socket broadcasts, global user lookup, administrator read path or table payloads.
All response bodies (including failures) are private/no-store.
"""
import base64
from datetime import datetime
import json
from uuid import UUID

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from vtt.campaigns.routes import _get_current_user
from vtt.extensions import db, limiter
from vtt.models import Campaign, CampaignMember, User
from vtt.models.private_conversation import PrivateConversation, PrivateMessage
from vtt.utils.time import utcnow

conversations_bp = Blueprint('private_conversations', __name__, url_prefix='/api/private-conversations')


class ConversationError(Exception):
    def __init__(self, message='not found', status=404):
        self.message, self.status = message, status


@conversations_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@conversations_bp.errorhandler(ConversationError)
def fail(error):
    db.session.rollback()
    return jsonify(error=error.message), error.status


def actor():
    user, error = _get_current_user()
    if error:
        raise ConversationError()
    return user


def positive(value):
    if type(value) is not int or not 0 < value < 2**31:
        raise ConversationError('invalid request', 400)
    return value


def body(keys):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != set(keys):
        raise ConversationError('invalid request', 400)
    return data


def member(campaign, user_id):
    user = db.session.get(User, user_id, populate_existing=True)
    if not user or not user.is_usable() or campaign.deleted_at is not None:
        return False
    if campaign.owner_id == user_id:
        return True
    return db.session.execute(select(CampaignMember.id).where(
        CampaignMember.campaign_id == campaign.id, CampaignMember.user_id == user_id,
        CampaignMember.status == 'active')).scalar_one_or_none() is not None


def scoped(conversation_id, user_id, *, write=False):
    query = select(PrivateConversation).where(PrivateConversation.id == conversation_id)
    if write:
        query = query.with_for_update().execution_options(populate_existing=True)
    conversation = db.session.execute(query).scalar_one_or_none()
    if not conversation or user_id not in (conversation.participant_low_id, conversation.participant_high_id):
        raise ConversationError()
    campaign = db.session.get(Campaign, conversation.campaign_id, populate_existing=True)
    if not campaign or not member(campaign, user_id):
        raise ConversationError()
    other_id = conversation.participant_high_id if user_id == conversation.participant_low_id else conversation.participant_low_id
    can_send = member(campaign, other_id)
    if write and not can_send:
        raise ConversationError('conversation is read-only', 409)
    return conversation, campaign, other_id, can_send


def instant(value):
    return value.isoformat(timespec='microseconds') + 'Z'


def metadata(row, user_id):
    conversation, campaign, other_id, can_send = scoped(row.id, user_id)
    partner = db.session.get(User, other_id)
    return dict(id=conversation.id, campaign_id=campaign.id, campaign_name=campaign.name,
                partner_id=other_id, partner_name=partner.username, self_user_id=user_id,
                can_send=can_send, updated_at=instant(conversation.updated_at))


def message_data(row):
    author = db.session.get(User, row.author_user_id)
    return dict(id=row.id, author_user_id=row.author_user_id, author_name=author.username,
                client_event_id=row.client_event_id, content=row.content, created_at=instant(row.created_at))


@conversations_bp.post('')
@limiter.limit('120 per hour')
@jwt_required()
def open_pair():
    user = actor(); data = body(('campaign_id', 'recipient_user_id'))
    campaign_id = positive(data['campaign_id']); recipient = positive(data['recipient_user_id'])
    if recipient == user.id:
        raise ConversationError('invalid request', 400)
    campaign = db.session.execute(select(Campaign).where(Campaign.id == campaign_id)
        .with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
    if not campaign or not member(campaign, user.id) or not member(campaign, recipient):
        raise ConversationError()
    low, high = sorted((user.id, recipient))
    row = PrivateConversation.query.filter_by(campaign_id=campaign_id, participant_low_id=low, participant_high_id=high).first()
    created = row is None
    if created:
        row = PrivateConversation(campaign_id=campaign_id, participant_low_id=low, participant_high_id=high)
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            # Defensive fallback for dialects without row locks; never commit a second pair.
            db.session.rollback()
            row = PrivateConversation.query.filter_by(campaign_id=campaign_id, participant_low_id=low, participant_high_id=high).first()
            if row is None:
                raise ConversationError('please retry', 409)
            created = False
    else:
        db.session.commit()
    return jsonify(conversation=metadata(row, user.id)), 201 if created else 200


@conversations_bp.get('')
@limiter.limit('1800 per hour')
@jwt_required()
def list_own():
    user = actor(); cursor = request.args.get('cursor'); after = None
    if cursor:
        try:
            if len(cursor) > 180:
                raise ValueError()
            at, row_id = json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4)))
            after = datetime.fromisoformat(at), positive(row_id)
            if after[0].tzinfo is not None:
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise ConversationError('invalid cursor', 400) from None
    query = (select(PrivateConversation).join(Campaign, Campaign.id == PrivateConversation.campaign_id)
        .outerjoin(CampaignMember, and_(CampaignMember.campaign_id == Campaign.id,
                                       CampaignMember.user_id == user.id, CampaignMember.status == 'active'))
        .where(Campaign.deleted_at.is_(None),
               or_(Campaign.owner_id == user.id, CampaignMember.id.is_not(None)),
               or_(PrivateConversation.participant_low_id == user.id, PrivateConversation.participant_high_id == user.id)))
    if after:
        at, row_id = after
        query = query.where(or_(PrivateConversation.updated_at < at,
                               and_(PrivateConversation.updated_at == at, PrivateConversation.id < row_id)))
    rows = db.session.execute(query.order_by(PrivateConversation.updated_at.desc(), PrivateConversation.id.desc()).limit(25)).scalars().all()
    page = rows[:24]
    next_cursor = base64.urlsafe_b64encode(json.dumps([page[-1].updated_at.isoformat(), page[-1].id]).encode()).decode().rstrip('=') if len(rows) > 24 else None
    return jsonify(conversations=[metadata(row, user.id) for row in page], next_cursor=next_cursor)


@conversations_bp.get('/<int:conversation_id>')
@limiter.limit('1800 per hour')
@jwt_required()
def read_conversation(conversation_id):
    user = actor(); conversation, _, _, _ = scoped(conversation_id, user.id)
    raw_before, raw_after = request.args.get('before'), request.args.get('after')
    if raw_before is not None and raw_after is not None:
        raise ConversationError('invalid cursor', 400)
    def cursor(value):
        if value is None:
            return None
        if not value.isascii() or not value.isdigit() or len(value) > 10:
            raise ConversationError('invalid cursor', 400)
        return positive(int(value))
    before, after = cursor(raw_before), cursor(raw_after)
    query = select(PrivateMessage).where(PrivateMessage.conversation_id == conversation.id)
    if before is not None:
        query = query.where(PrivateMessage.id < before)
    if after is not None:
        query = query.where(PrivateMessage.id > after)
    rows = db.session.execute(query.order_by(PrivateMessage.id.asc() if after is not None else PrivateMessage.id.desc()).limit(51)).scalars().all()
    page = rows[:50]
    if after is None:
        page.reverse()
    return jsonify(conversation=metadata(conversation, user.id), messages=[message_data(row) for row in page],
                   more=len(rows) > 50, oldest_id=page[0].id if page else None, newest_id=page[-1].id if page else None)


@conversations_bp.post('/<int:conversation_id>/messages')
@limiter.limit('600 per hour')
@jwt_required()
def send_message(conversation_id):
    user = actor(); data = body(('content', 'client_event_id'))
    content = data['content']
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 2000 or len(content) > 2000 or '\x00' in content:
        raise ConversationError('invalid message', 400)
    try:
        content.encode('utf-8')
    except UnicodeError:
        raise ConversationError('invalid message', 400) from None
    try:
        event_id = str(UUID(data['client_event_id']))
    except (ValueError, TypeError, AttributeError):
        raise ConversationError('invalid request', 400) from None
    conversation, _, _, _ = scoped(conversation_id, user.id, write=True)
    # Current participation is checked before replay as well as before a new write.
    old = PrivateMessage.query.filter_by(conversation_id=conversation.id, author_user_id=user.id, client_event_id=event_id).first()
    if old:
        if old.content != content:
            raise ConversationError('request id already used', 409)
        return jsonify(message=message_data(old), replayed=True), 200
    row = PrivateMessage(conversation_id=conversation.id, author_user_id=user.id, client_event_id=event_id, content=content)
    db.session.add(row); conversation.updated_at = utcnow()
    db.session.commit()
    return jsonify(message=message_data(row), replayed=False), 201
