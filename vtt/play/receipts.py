"""Bounded at-most-once application commands, including unknown outcomes.

An uncompleted claim never authorizes replaying its side effects. The caller must
resync instead. Existing APIs without a request ID keep their legacy contract.
"""

from datetime import timedelta
from functools import wraps
from hashlib import sha256
import json

from flask import g, jsonify, make_response, request
from sqlalchemy.exc import IntegrityError

from vtt.extensions import db
from vtt.models.character_hotbar import TableRequestReceipt
from vtt.utils.time import utcnow


def claim(context, request_id, operation, payload):
    if not isinstance(request_id, str) or not 8 <= len(request_id) <= 120:
        return None, ({"error": "request_id_required"}, 400)
    try:
        digest = sha256(json.dumps([operation, payload], sort_keys=True, separators=(",", ":"),
                                  allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError):
        return None, ({"error": "invalid_request"}, 400)
    # Expired claims have an explicit 24h boundary; never claim unlimited replay safety.
    TableRequestReceipt.query.filter(TableRequestReceipt.expires_at < utcnow()).delete(synchronize_session=False)
    receipt = TableRequestReceipt(context_id=context.id, user_id=context.user_id,
                                  request_id=request_id, request_digest=digest,
                                  expires_at=utcnow() + timedelta(hours=24))
    db.session.add(receipt)
    try:
        db.session.commit()
        return receipt, None
    except IntegrityError:
        db.session.rollback()
    existing = TableRequestReceipt.query.filter_by(context_id=context.id, request_id=request_id).first()
    if existing is None:
        return None, ({"error": "request_conflict"}, 409)
    if existing.request_digest != digest:
        return None, ({"error": "request_id_reused"}, 409)
    if existing.status_code is None:
        return None, ({"error": "request_in_progress", "message": "Bitte Tischzustand abgleichen; dieselbe Aktion wird nicht erneut ausgeführt."}, 409)
    return None, (existing.response, existing.status_code)


def finish(receipt, payload, status=200):
    receipt.response = payload
    receipt.status_code = status
    db.session.commit()


def idempotent_table_request(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        context = getattr(g, "table_context", None)
        body = request.get_json(silent=True)
        request_id = body.get("request_id") if isinstance(body, dict) else None
        if context is None or request_id is None:
            return handler(*args, **kwargs)
        receipt, replay = claim(context, request_id, request.path, body)
        if replay:
            payload, status = replay
            response = make_response(jsonify(payload), status)
            response.headers["X-Request-Replayed"] = "true"
            return response
        response = make_response(handler(*args, **kwargs))
        payload = response.get_json(silent=True)
        finish(receipt, payload, response.status_code)
        response.headers["X-Request-ID"] = request_id
        return response
    return wrapped


def socket_roll(context, payload, handler):
    request_id = payload.get("client_event_id") if isinstance(payload, dict) else None
    if request_id is None:
        return handler()
    receipt, replay = claim(context, request_id, "socket:roll_dice", payload)
    if replay:
        answer, status = replay
        return answer if status == 200 else {**answer, "status": status}
    answer = handler()
    finish(receipt, answer, 200)
    return answer
