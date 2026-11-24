"""FV15: campaign-quota requests and explicit owner/admin review.

The requester is always the cookie-JWT actor; no endpoint accepts an actor ID.
Mutations also require ``X-Quota-Account`` to equal that actor so a page that
switched accounts cannot act for the previous one. Every mutation is one
transaction: requester User row first, then the request row, with
compare-and-set updates so a stale or repeated action changes nothing.
AuditLog rows are added inside that transaction; vtt.utils.audit.log_audit
commits on its own and is deliberately not used here.

A NULL or zero quota keeps its existing meaning (User.can_create_campaign()
returns False); it is shown as unassigned and never treated as unlimited.
"""

from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db, limiter
from vtt.models import AuditLog, Campaign, User
from vtt.models.campaign_quota_request import CampaignQuotaRequest
from vtt.utils.time import utcnow


campaign_quota_bp = Blueprint('campaign_quota', __name__, url_prefix='/api/campaign-quota')

INT_MAX = 2147483647
DAILY_LIMIT = 5
OWN_HISTORY = 20
REVIEW_PAGE = 50
CREATOR_TIERS = frozenset({'dm', 'headmaster'})
CREATOR_PLATFORM_ROLES = frozenset({'admin', 'owner'})
REVIEW_ROLES = frozenset({'owner', 'admin'})
ACCOUNT_HEADER = 'X-Quota-Account'


@campaign_quota_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def _error(code, http_status, **extra):
    return jsonify(error=code, **extra), http_status


def _identity():
    try:
        identity = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    return identity if identity > 0 else None


def _usable(user):
    return user if user is not None and user.is_usable() else None


def _account_matches(identity):
    return request.headers.get(ACCOUNT_HEADER, '') == str(identity)


def _lock_user(user_id):
    return db.session.get(User, user_id, with_for_update=True, populate_existing=True)


def _strict_int(value, minimum, maximum=INT_MAX):
    # bool is an int subclass; JSON true/false must not count as a total.
    return type(value) is int and minimum <= value <= maximum


def _text(value, required):
    if value is None and not required:
        return True, None
    if not isinstance(value, str):
        return False, None
    text = value.replace('\r\n', '\n').replace('\r', '\n').strip()
    if required and not text:
        return False, None
    if len(text) > CampaignQuotaRequest.TEXT_MAX:
        return False, None
    if any(ord(char) < 32 and char not in '\n\t' for char in text) or '\x7f' in text:
        return False, None
    return True, text or None


def _finite_quota(user):
    quota = user.active_campaigns_quota
    return quota if _strict_int(quota, 1) else None


def _is_creator(user):
    return user.profile_tier in CREATOR_TIERS or user.platform_role in CREATOR_PLATFORM_ROLES


def _ineligibility(user):
    """Request eligibility deliberately ignores remaining capacity."""
    if not _is_creator(user):
        return 'creator_role_required'
    if user.active_campaigns_quota is None:
        return 'quota_unassigned'
    quota = _finite_quota(user)
    if quota is None:
        return 'quota_not_positive'
    if quota >= INT_MAX:
        return 'quota_at_maximum'
    return None


def _can_review(user):
    return user.platform_role in REVIEW_ROLES


def _quota_view(user):
    quota = user.active_campaigns_quota
    return dict(current=quota if _strict_int(quota, 0) else None,
                assigned=quota is not None,
                active_count=user.get_active_campaigns_count())


def _iso(value):
    return value.isoformat() if value else None


def _own_row(row):
    return dict(id=row.id, status=row.status, submitted_quota=row.current_quota,
                desired_total=row.desired_total, reason=row.reason,
                created_at=_iso(row.created_at), decided_at=_iso(row.decided_at),
                approved_total=row.approved_total, reviewer_note=row.reviewer_note)


def _window_start():
    return utcnow() - timedelta(hours=24)


def _recent_count(user_id):
    return CampaignQuotaRequest.query.filter(
        CampaignQuotaRequest.requester_id == user_id,
        CampaignQuotaRequest.created_at >= _window_start(),
    ).count()


def _audit(action, requester_id, performer_id, row, **details):
    db.session.add(AuditLog(
        user_id=requester_id, performed_by_id=performer_id, action=action,
        resource_type='campaign_quota_request', resource_id=row.id,
        details=dict(request_id=row.id, **details),
        ip_address=request.remote_addr, timestamp=utcnow(),
    ))


def _payload(required, optional=frozenset()):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None
    keys = set(payload)
    if not required <= keys or not keys <= (required | optional):
        return None
    return payload


def _empty_body():
    if not request.get_data(cache=True):
        return True
    payload = request.get_json(silent=True)
    return isinstance(payload, dict) and not payload


@campaign_quota_bp.get('/requests')
@jwt_required()
def own_requests():
    identity = _identity()
    user = _usable(db.session.get(User, identity)) if identity else None
    if not user:
        return _error('authentication_required', 401)
    rows = CampaignQuotaRequest.query.filter_by(requester_id=user.id).order_by(
        CampaignQuotaRequest.created_at.desc(), CampaignQuotaRequest.id.desc(),
    ).limit(OWN_HISTORY).all()
    reason = _ineligibility(user)
    return jsonify(
        accountId=user.id,
        quota=_quota_view(user),
        eligible=reason is None,
        ineligible_reason=reason,
        can_review=_can_review(user),
        limits=dict(max_total=INT_MAX, text_max=CampaignQuotaRequest.TEXT_MAX,
                    per_24h=DAILY_LIMIT, used_24h=_recent_count(user.id)),
        requests=[_own_row(row) for row in rows],
    )


@campaign_quota_bp.post('/requests')
@jwt_required()
@limiter.limit('10 per minute')
def submit_request():
    identity = _identity()
    if not identity:
        return _error('authentication_required', 401)
    if not _account_matches(identity):
        return _error('account_mismatch', 403)
    payload = _payload({'desired_total', 'reason'})
    if payload is None:
        return _error('invalid_quota_request', 400)
    desired = payload['desired_total']
    if not _strict_int(desired, 1):
        return _error('invalid_desired_total', 400)
    valid, reason_text = _text(payload['reason'], required=True)
    if not valid:
        return _error('invalid_reason', 400)

    user = _usable(_lock_user(identity))
    if not user:
        db.session.rollback()
        return _error('authentication_required', 401)
    ineligible = _ineligibility(user)
    if ineligible:
        db.session.rollback()
        return _error(ineligible, 403)
    quota = _finite_quota(user)
    if desired <= quota:
        db.session.rollback()
        return _error('desired_total_not_above_current', 400, current_quota=quota)
    pending = CampaignQuotaRequest.query.filter_by(pending_key=user.id).first()
    if pending:
        db.session.rollback()
        return _error('pending_request_exists', 409, request_id=pending.id)
    if _recent_count(user.id) >= DAILY_LIMIT:
        db.session.rollback()
        return _error('request_rate_limited', 429, per_24h=DAILY_LIMIT)

    row = CampaignQuotaRequest(requester_id=user.id, current_quota=quota, desired_total=desired,
                               reason=reason_text, status='pending', pending_key=user.id,
                               created_at=utcnow())
    try:
        db.session.add(row)
        db.session.flush()
        _audit('campaign_quota_requested', user.id, user.id, row,
               old_quota=quota, new_quota=quota, desired_total=desired)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # A concurrent submission won the unique pending_key; anything else is a real fault.
        pending = CampaignQuotaRequest.query.filter_by(pending_key=identity).first()
        if not pending:
            raise
        return _error('pending_request_exists', 409, request_id=pending.id)
    return jsonify(accountId=user.id, request=_own_row(row),
                   quota=_quota_view(user), quota_changed=False), 201


@campaign_quota_bp.post('/requests/<int:request_id>/cancel')
@jwt_required()
@limiter.limit('20 per minute')
def cancel_request(request_id):
    identity = _identity()
    if not identity:
        return _error('authentication_required', 401)
    if not _account_matches(identity):
        return _error('account_mismatch', 403)
    if not _empty_body():
        return _error('invalid_quota_request', 400)
    user = _usable(_lock_user(identity))
    if not user:
        db.session.rollback()
        return _error('authentication_required', 401)
    row = CampaignQuotaRequest.query.filter_by(id=request_id, requester_id=user.id) \
        .with_for_update().populate_existing().first()
    if not row:
        db.session.rollback()
        return _error('request_not_found', 404)
    if row.status != 'pending':
        db.session.rollback()
        return _error('request_not_pending', 409, request=_own_row(row), quota_changed=False)
    now = utcnow()
    changed = CampaignQuotaRequest.query.filter_by(
        id=row.id, requester_id=user.id, status='pending',
    ).update(dict(status='cancelled', pending_key=None, decided_at=now), synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        return _error('request_not_pending', 409, quota_changed=False)
    _audit('campaign_quota_request_cancelled', user.id, user.id, row,
           old_quota=user.active_campaigns_quota, new_quota=user.active_campaigns_quota)
    db.session.commit()
    db.session.refresh(row)
    return jsonify(accountId=user.id, request=_own_row(row),
                   quota=_quota_view(user), quota_changed=False)


def _reviewer(identity):
    user = _usable(db.session.get(User, identity)) if identity else None
    if not user:
        return None, _error('authentication_required', 401)
    if not _can_review(user):
        return None, _error('forbidden', 403)
    return user, None


@campaign_quota_bp.get('/review-requests')
@jwt_required()
def review_requests():
    reviewer, failure = _reviewer(_identity())
    if failure:
        return failure
    if set(request.args) - {'view'}:
        return _error('invalid_review_query', 400)
    view = request.args.get('view', 'pending')
    if view not in {'pending', 'closed'}:
        return _error('invalid_review_query', 400)
    query = db.session.query(CampaignQuotaRequest, User.id, User.username, User.active_campaigns_quota) \
        .join(User, User.id == CampaignQuotaRequest.requester_id)
    if view == 'pending':
        query = query.filter(CampaignQuotaRequest.status == 'pending').order_by(
            CampaignQuotaRequest.created_at.asc(), CampaignQuotaRequest.id.asc())
    else:
        query = query.filter(CampaignQuotaRequest.status != 'pending').order_by(
            CampaignQuotaRequest.decided_at.desc(), CampaignQuotaRequest.id.desc())
    rows = query.limit(REVIEW_PAGE + 1).all()
    shown = rows[:REVIEW_PAGE]
    requester_ids = {user_id for _, user_id, _, _ in shown}
    active = dict(db.session.query(Campaign.owner_id, func.count(Campaign.id)).filter(
        Campaign.owner_id.in_(requester_ids), Campaign.status == 'active',
    ).group_by(Campaign.owner_id).all()) if requester_ids else {}
    entries = []
    for row, user_id, username, live_quota in shown:
        entries.append(dict(
            id=row.id, status=row.status,
            requester=dict(id=user_id, username=username),
            submitted_quota=row.current_quota, desired_total=row.desired_total, reason=row.reason,
            created_at=_iso(row.created_at), decided_at=_iso(row.decided_at),
            approved_total=row.approved_total, reviewer_note=row.reviewer_note,
            live=dict(current=live_quota if _strict_int(live_quota, 0) else None,
                      assigned=live_quota is not None, active_count=int(active.get(user_id, 0))),
        ))
    return jsonify(accountId=reviewer.id, view=view, entries=entries,
                   complete=len(rows) <= REVIEW_PAGE, limit=REVIEW_PAGE)


def _decision_payload():
    payload = _payload({'decision', 'expected_current_quota'}, frozenset({'approved_total', 'reviewer_note'}))
    if payload is None or payload['decision'] not in ('approve', 'reject'):
        return None, 'invalid_review_decision'
    expected = payload['expected_current_quota']
    if expected is not None and not _strict_int(expected, 0):
        return None, 'invalid_expected_quota'
    approved = payload.get('approved_total')
    if payload['decision'] == 'approve':
        if not _strict_int(approved, 1):
            return None, 'invalid_approved_total'
    elif approved is not None:
        return None, 'invalid_approved_total'
    valid, note = _text(payload.get('reviewer_note'), required=False)
    if not valid:
        return None, 'invalid_reviewer_note'
    return dict(decision=payload['decision'], expected=expected, approved=approved, note=note), None


@campaign_quota_bp.post('/review-requests/<int:request_id>/decision')
@jwt_required()
@limiter.limit('30 per minute')
def review_decision(request_id):
    identity = _identity()
    if not identity:
        return _error('authentication_required', 401)
    if not _account_matches(identity):
        return _error('account_mismatch', 403)
    reviewer, failure = _reviewer(identity)
    if failure:
        return failure
    decision, invalid = _decision_payload()
    if invalid:
        return _error(invalid, 400)
    located = db.session.get(CampaignQuotaRequest, request_id)
    if not located:
        return _error('request_not_found', 404)
    # Canonical lock order: requester User first, then the request row (refreshed).
    requester = _lock_user(located.requester_id)
    row = CampaignQuotaRequest.query.filter_by(id=request_id) \
        .with_for_update().populate_existing().first()
    if not requester or not row:
        db.session.rollback()
        return _error('request_not_found', 404)

    def conflict(code):
        live, status = _quota_view(requester), row.status
        db.session.rollback()
        return _error(code, 409, status=status, live=live, mutated=False)

    if row.status != 'pending':
        return conflict('request_not_pending')
    live_quota = requester.active_campaigns_quota
    if live_quota != decision['expected']:
        return conflict('quota_changed')

    new_quota = live_quota
    if decision['decision'] == 'approve':
        finite = _finite_quota(requester)
        if finite is None:
            return conflict('quota_not_finite')
        approved = decision['approved']
        if approved <= finite:
            db.session.rollback()
            return _error('approved_total_not_above_current', 400, current_quota=finite)
        active = requester.get_active_campaigns_count()
        if approved < active:
            db.session.rollback()
            return _error('approved_total_below_active', 400, active_count=active)
        # Compare-and-set on the live value: only an unchanged quota is raised.
        if User.query.filter(User.id == requester.id, User.active_campaigns_quota == finite) \
                .update({'active_campaigns_quota': approved}, synchronize_session=False) != 1:
            return conflict('quota_changed')
        new_quota = approved

    status = 'approved' if decision['decision'] == 'approve' else 'rejected'
    now = utcnow()
    changed = CampaignQuotaRequest.query.filter_by(id=row.id, status='pending').update(dict(
        status=status, pending_key=None, reviewer_id=reviewer.id, reviewer_note=decision['note'],
        decided_at=now, approved_total=new_quota if status == 'approved' else None,
    ), synchronize_session=False)
    if changed != 1:
        return conflict('request_not_pending')
    _audit('campaign_quota_request_' + status, requester.id, reviewer.id, row,
           old_quota=live_quota, new_quota=new_quota, desired_total=row.desired_total)
    db.session.commit()
    db.session.refresh(row)
    db.session.refresh(requester)
    return jsonify(
        accountId=reviewer.id, id=row.id, status=row.status, approved_total=row.approved_total,
        reviewer_note=row.reviewer_note, decided_at=_iso(row.decided_at),
        requester=dict(id=requester.id, username=requester.username),
        live=_quota_view(requester), quota_changed=new_quota != live_quota,
    )
