"""Bounded review features; parent-resource authority is checked on every operation."""
import hashlib
import json
from uuid import UUID

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from vtt.campaigns.routes import _is_dm
from vtt.conversations import ConversationError, actor, member, scoped
from vtt.extensions import db, limiter
from vtt.models import Campaign, User
from vtt.models.review_domain import AtlasCampaignLink, ReviewThread, ReviewThreadMessage

review_domain_bp = Blueprint('review_domain', __name__, url_prefix='/api/review-domain')


@review_domain_bp.after_request
def private(response):
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@review_domain_bp.errorhandler(ConversationError)
def denied(error):
    db.session.rollback()
    return jsonify(error=error.message), error.status


def fail(message='not found', status=404):
    raise ConversationError(message, status)


def text(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum or len(value) > maximum or '\x00' in value:
        fail('invalid text', 400)
    try:
        value.encode('utf-8')
    except UnicodeError:
        fail('invalid text', 400)
    return value.strip()


def positive(value):
    if type(value) is not int or not 0 < value < 2**31:
        fail('invalid id', 400)
    return value


def uuid(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        fail('invalid request id', 400)


def body(keys):
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) != set(keys):
        fail('invalid request', 400)
    return value


def parent_access(kind, identity, user, write=False):
    identity = positive(identity)
    if kind == 'private':
        conversation, campaign, _, can_send = scoped(identity, user.id, write=write)
        # The private parent's fixed pair remains the only audience.
        return conversation, can_send
    if kind != 'campaign':
        fail('invalid parent', 400)
    from vtt.campaign_rooms import room
    from vtt.community import service
    campaign = room(user, identity)
    if not campaign:
        fail()
    if service.active_sanctions(campaign.id, user.id, {'ban'}):
        fail('forbidden', 403)
    can_send = not service.active_sanctions(campaign.id, user.id, {'mute'})
    context = getattr(g, 'table_context', None)
    if context:
        from vtt.play.contexts import current_role
        can_send = can_send and current_role(campaign.id, user.id, context.game_session_id) in {'DM', 'CO_DM', 'PLAYER'}
    if write and not can_send:
        fail('read only', 403)
    return campaign, bool(can_send)


def thread_parent(row):
    return ('private', row.private_conversation_id) if row.private_conversation_id else ('campaign', row.campaign_id)


def thread_access(identity, user, write=False):
    statement = select(ReviewThread).where(ReviewThread.id == identity)
    if write:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    row = db.session.execute(statement).scalar_one_or_none()
    if not row:
        fail()
    kind, parent_id = thread_parent(row)
    _, can_send = parent_access(kind, parent_id, user, write=write)
    return row, can_send


def thread_data(row, user, can_send):
    kind, parent_id = thread_parent(row)
    return dict(id=row.id, kind=kind, parent_id=parent_id, title=row.title, revision=row.revision,
                closed=row.closed, can_send=can_send and not row.closed,
                can_edit=can_send and row.created_by == user.id, created_at=row.created_at.isoformat() + 'Z')


def message_data(row):
    author = db.session.get(User, row.author_id)
    return dict(id=row.id, author_user_id=row.author_id, author_name=author.username if author else '?',
                request_id=row.request_id, content=row.content, created_at=row.created_at.isoformat() + 'Z')


@review_domain_bp.route('/threads', methods=['GET', 'POST'])
@jwt_required()
@limiter.limit('120 per minute')
def threads():
    user = actor()
    if request.method == 'GET':
        try:
            kind = request.args.get('kind')
            parent_id = int(request.args.get('parent_id', ''))
            after = int(request.args.get('after', '0'))
            if after < 0 or after >= 2**31:
                raise ValueError
        except (ValueError, TypeError):
            fail('invalid cursor', 400)
        _, can_send = parent_access(kind, parent_id, user)
        column = ReviewThread.private_conversation_id if kind == 'private' else ReviewThread.campaign_id
        rows = ReviewThread.query.filter(column == parent_id, ReviewThread.id > after).order_by(ReviewThread.id).limit(51).all()
        return jsonify(threads=[thread_data(row, user, can_send) for row in rows[:50]], can_create=can_send,
                       next_after=rows[49].id if len(rows) > 50 else None)
    data = body(('kind', 'parent_id', 'title', 'request_id'))
    kind, parent_id = data['kind'], positive(data['parent_id'])
    title, request_id = text(data['title'], 100), uuid(data['request_id'])
    parent, can_send = parent_access(kind, parent_id, user, write=True)
    # Parent row serializes creation on PostgreSQL; uniqueness handles concurrent SQLite requests.
    db.session.refresh(parent, with_for_update=True)
    parent_access(kind, parent_id, user, write=True)
    old = ReviewThread.query.filter_by(created_by=user.id, request_id=request_id).first()
    if old:
        if thread_parent(old) != (kind, parent_id) or old.request_title != title:
            fail('request id reused', 409)
        return jsonify(thread=thread_data(old, user, can_send), replayed=True)
    row = ReviewThread(created_by=user.id, request_id=request_id, request_title=title, title=title,
                       private_conversation_id=parent_id if kind == 'private' else None,
                       campaign_id=parent_id if kind == 'campaign' else None)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        parent_access(kind, parent_id, user, write=True)
        row = ReviewThread.query.filter_by(created_by=user.id, request_id=request_id).first()
        if not row or thread_parent(row) != (kind, parent_id) or row.request_title != title:
            fail('request conflict', 409)
        return jsonify(thread=thread_data(row, user, can_send), replayed=True)
    return jsonify(thread=thread_data(row, user, can_send), replayed=False), 201


@review_domain_bp.route('/threads/<int:identity>', methods=['GET', 'PUT'])
@jwt_required()
@limiter.limit('120 per minute')
def thread(identity):
    user = actor()
    row, can_send = thread_access(identity, user, write=request.method == 'PUT')
    if request.method == 'PUT':
        data = body(('revision', 'title', 'closed'))
        if row.created_by != user.id:
            fail()
        if type(data['revision']) is not int or data['revision'] != row.revision:
            fail('revision conflict', 409)
        if type(data['closed']) is not bool:
            fail('invalid state', 400)
        row.title = text(data['title'], 100)
        row.closed = data['closed']
        row.revision += 1
        db.session.commit()
        return jsonify(thread=thread_data(row, user, can_send))
    try:
        before, after = int(request.args.get('before', '0')), int(request.args.get('after', '0'))
        if before < 0 or after < 0 or max(before, after) >= 2**31 or (before and after):
            raise ValueError
    except (ValueError, TypeError):
        fail('invalid cursor', 400)
    query = ReviewThreadMessage.query.filter_by(thread_id=row.id)
    if before:
        query = query.filter(ReviewThreadMessage.id < before)
    if after:
        query = query.filter(ReviewThreadMessage.id > after)
    rows = query.order_by(ReviewThreadMessage.id.asc() if after else ReviewThreadMessage.id.desc()).limit(51).all()
    page = rows[:50]
    if not after:
        page.reverse()
    return jsonify(thread=thread_data(row, user, can_send), messages=[message_data(message) for message in page],
                   more=len(rows) > 50, oldest_id=page[0].id if page else None, newest_id=page[-1].id if page else None)


@review_domain_bp.post('/threads/<int:identity>/messages')
@jwt_required()
@limiter.limit('60 per minute')
def send(identity):
    user = actor()
    data = body(('content', 'request_id'))
    content, request_id = text(data['content'], 2000), uuid(data['request_id'])
    row, _ = thread_access(identity, user, write=True)
    old = ReviewThreadMessage.query.filter_by(thread_id=row.id, author_id=user.id, request_id=request_id).first()
    if old:
        if old.content != content:
            fail('request id reused', 409)
        return jsonify(message=message_data(old), replayed=True)
    if row.closed:
        fail('thread closed', 409)
    message = ReviewThreadMessage(thread_id=row.id, author_id=user.id, request_id=request_id, content=content)
    db.session.add(message)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        thread_access(identity, user, write=True)
        old = ReviewThreadMessage.query.filter_by(thread_id=row.id, author_id=user.id, request_id=request_id).first()
        if old is None or old.content != content:
            fail('request conflict', 409)
        return jsonify(message=message_data(old), replayed=True)
    return jsonify(message=message_data(message), replayed=False), 201


def world_access(identity, user, *, write=False):
    from vtt.atlas import access, publication, writing
    from vtt.atlas_domain import AtlasError
    g.atlas_actor = user.id
    try:
        if write:
            return writing(identity, owner=True), 'owner'
        world, permission = access(identity)
        if permission == 'reader' and not publication(world):
            fail()
        return world, permission
    except AtlasError:
        fail()


def campaign_access(identity, user, *, write=False):
    campaign = db.session.get(Campaign, positive(identity), populate_existing=True)
    if not campaign or not member(campaign, user.id) or (write and not _is_dm(campaign, user.id)):
        fail()
    return campaign


def link_data(row, campaign):
    return dict(campaign_id=campaign.id, name=campaign.name, revision=row.revision, href='/campaigns?campaign_id=' + str(campaign.id))


@review_domain_bp.get('/managed-campaigns')
@jwt_required()
def managed_campaigns():
    from vtt.models import CampaignMember
    user = actor()
    member_ids = select(CampaignMember.campaign_id).where(CampaignMember.user_id == user.id, CampaignMember.status == 'active')
    rows = Campaign.query.filter(Campaign.deleted_at.is_(None), (Campaign.owner_id == user.id) | Campaign.id.in_(member_ids)).order_by(Campaign.name).limit(100).all()
    return jsonify(campaigns=[dict(id=row.id, name=row.name) for row in rows if _is_dm(row, user.id)])


@review_domain_bp.route('/worlds/<uuid:identity>/campaigns', methods=['GET', 'POST'])
@jwt_required()
@limiter.limit('60 per minute')
def world_campaigns(identity):
    user = actor()
    world, permission = world_access(identity, user, write=request.method == 'POST')
    if request.method == 'GET':
        rows = AtlasCampaignLink.query.filter_by(world_id=world.id).order_by(AtlasCampaignLink.campaign_id).limit(50).all()
        result = []
        for row in rows:
            campaign = db.session.get(Campaign, row.campaign_id, populate_existing=True)
            if campaign and member(campaign, user.id):
                result.append(link_data(row, campaign))
        return jsonify(world_revision=world.revision, can_manage=permission == 'owner', campaigns=result)
    data = body(('campaign_id', 'world_revision', 'request_id'))
    campaign = campaign_access(data['campaign_id'], user, write=True)
    request_id = uuid(data['request_id'])
    old = AtlasCampaignLink.query.filter_by(created_by=user.id, request_id=request_id).first()
    if old:
        if old.world_id != world.id or old.campaign_id != campaign.id:
            fail('request id reused', 409)
        return jsonify(link=link_data(old, campaign), world_revision=world.revision, replayed=True)
    if type(data['world_revision']) is not int or data['world_revision'] != world.revision:
        fail('revision conflict', 409)
    old = db.session.get(AtlasCampaignLink, (world.id, campaign.id))
    if old:
        fail('already linked', 409)
    if AtlasCampaignLink.query.filter_by(world_id=world.id).count() >= 50:
        fail('link limit', 409)
    row = AtlasCampaignLink(world_id=world.id, campaign_id=campaign.id, created_by=user.id, request_id=request_id)
    db.session.add(row)
    world.revision += 1
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        world, _ = world_access(identity, user, write=True)
        campaign = campaign_access(data['campaign_id'], user, write=True)
        old = AtlasCampaignLink.query.filter_by(created_by=user.id, request_id=request_id).first()
        if not old or old.world_id != world.id or old.campaign_id != campaign.id:
            fail('request conflict', 409)
        return jsonify(link=link_data(old, campaign), world_revision=world.revision, replayed=True)
    return jsonify(link=link_data(row, campaign), world_revision=world.revision, replayed=False), 201


@review_domain_bp.delete('/worlds/<uuid:identity>/campaigns/<int:campaign_id>')
@jwt_required()
@limiter.limit('60 per minute')
def unlink_world(identity, campaign_id):
    user = actor()
    world, _ = world_access(identity, user, write=True)
    campaign_access(campaign_id, user, write=True)
    data = body(('world_revision', 'revision'))
    row = db.session.get(AtlasCampaignLink, (world.id, campaign_id), with_for_update=True, populate_existing=True)
    if not row:
        fail()
    if type(data['world_revision']) is not int or data['world_revision'] != world.revision or type(data['revision']) is not int or data['revision'] != row.revision:
        fail('revision conflict', 409)
    db.session.delete(row)
    world.revision += 1
    db.session.commit()
    return jsonify(world_revision=world.revision)


def companion_revision(char):
    stored = (char.character_data or {}).get('srdCompanions', [])
    return hashlib.sha256(json.dumps(stored, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@review_domain_bp.route('/characters/<int:identity>/companion-scaling', methods=['GET', 'PUT'])
@jwt_required()
@limiter.limit('120 per minute')
def companion_scaling(identity):
    from copy import deepcopy
    from sqlalchemy.orm.attributes import flag_modified
    from vtt.characters import srd_manage, sheet_link
    from vtt.characters.srd_creator import _progression_character
    from vtt.characters.srd_progression import ProgressionError
    user, char, _, error = _progression_character(identity, write='owner' if request.method == 'PUT' else False)
    if error:
        return error
    if request.method == 'PUT':
        data = body(('revision', 'companion_id', 'scaling'))
        if data['revision'] != companion_revision(char):
            fail('revision conflict', 409)
        effective = srd_manage.companions(char)
        target = next((row for row in effective if row.get('id') == data['companion_id']), None)
        if target is None:
            fail()
        try:
            config = srd_manage.scaling_config(data['scaling'])
        except ProgressionError as error:
            return jsonify(error=error.code, message=str(error)), error.status
        target['scaling'] = config
        # Preserve damage while changing the owner's explicit formula.
        damage = max(0, target['hpMax'] - target['hpCurrent'])
        maximum = srd_manage.scaled_companion_max(char, target)
        target['hpMax'], target['hpCurrent'] = maximum, max(0, maximum - damage)
        values = deepcopy(char.character_data)
        values['srdCompanions'] = effective
        char.character_data = values
        flag_modified(char, 'character_data')
        db.session.commit()
    evaluated = sheet_link.srd_evaluation(char) or {}
    return jsonify(revision=companion_revision(char), companions=srd_manage.companions(char),
                   level=evaluated.get('level', char.level), proficiency_bonus=evaluated.get('proficiencyBonus', char.proficiency_bonus),
                   can_edit=char.user_id == user.id)
