"""Small owner-visible profile and explicitly requested print analytics.

Neither endpoint accepts an actor ID. Counts are factual inventory, not scores;
printing records only a confirmed request through our UI.
"""

import re
from uuid import UUID

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db, limiter
from vtt.models import Campaign, CampaignMember, Character, User
from vtt.models.review_web import ReviewPrintRequest


review_web_bp = Blueprint('review_web', __name__, url_prefix='/api/review-web')
_REFERENCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}\Z')


@review_web_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def _actor():
    try:
        identity = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, identity)
    return user if user and user.is_usable() else None


@review_web_bp.get('/profile')
@jwt_required()
def own_profile():
    user = _actor()
    if not user:
        return jsonify(error='authentication_required'), 401
    link = user.discord_identity_link
    avatar = link.avatar_url() if link and link.is_active() else None
    return jsonify(
        user_id=user.id,
        username=user.username,
        avatar_url=avatar,
        characters=Character.query.filter_by(user_id=user.id, deleted_at=None).count(),
        owned_campaigns=Campaign.query.filter_by(owner_id=user.id, deleted_at=None).count(),
        memberships=CampaignMember.query.join(Campaign).filter(
            CampaignMember.user_id == user.id,
            CampaignMember.status == 'active', Campaign.deleted_at.is_(None),
        ).count(),
    )


def _same_request(row, ruleset, document_id):
    if row.ruleset != ruleset or row.document_id != document_id:
        return jsonify(error='request_conflict'), 409
    return jsonify(recorded=True, duplicate=True)


@review_web_bp.post('/print-requests')
@jwt_required()
@limiter.limit('12 per minute')
def record_print_request():
    user = _actor()
    if not user:
        return jsonify(error='authentication_required'), 401
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {'request_id', 'ruleset', 'document_id'}:
        return jsonify(error='invalid_print_request'), 400
    try:
        raw_key = payload['request_id']
        if not isinstance(raw_key, str) or len(raw_key) != 36:
            raise ValueError()
        key = str(UUID(raw_key))
    except (ValueError, TypeError, AttributeError):
        return jsonify(error='invalid_request_id'), 400
    ruleset, document_id = payload['ruleset'], payload['document_id']
    if any(not isinstance(value, str) or not _REFERENCE.fullmatch(value)
           for value in (ruleset, document_id)):
        return jsonify(error='invalid_document_reference'), 400
    existing = ReviewPrintRequest.query.filter_by(user_id=user.id, request_id=key).first()
    if existing:
        return _same_request(existing, ruleset, document_id)
    row = ReviewPrintRequest(user_id=user.id, request_id=key, ruleset=ruleset, document_id=document_id)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = ReviewPrintRequest.query.filter_by(user_id=user.id, request_id=key).first()
        if existing:
            return _same_request(existing, ruleset, document_id)
        raise
    return jsonify(recorded=True), 201


@review_web_bp.get('/print-requests/summary')
@jwt_required()
def print_summary():
    user = _actor()
    if not user:
        return jsonify(error='authentication_required'), 401
    if user.platform_role not in {'owner', 'admin'}:
        return jsonify(error='forbidden'), 403
    rows = db.session.query(
        ReviewPrintRequest.ruleset, ReviewPrintRequest.document_id,
        func.count(ReviewPrintRequest.id),
    ).group_by(ReviewPrintRequest.ruleset, ReviewPrintRequest.document_id).order_by(
        ReviewPrintRequest.ruleset, ReviewPrintRequest.document_id,
    ).limit(201).all()
    return jsonify(
        metric='confirmed_ui_print_requests',
        total=ReviewPrintRequest.query.count(),
        entries=[dict(ruleset=ruleset, document_id=document, count=count)
                 for ruleset, document, count in rows[:200]],
        complete=len(rows) <= 200,
    )
