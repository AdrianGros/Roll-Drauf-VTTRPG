"""REST uses authenticated local identities and the shared projected gateway."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge

from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.kernel.records import refuse
from .common import command_gateway, exact_object, gateway, principal, public_error

blueprint = Blueprint("creation_engine", __name__)


@blueprint.before_request
@jwt_required()
def authenticate():
    gateway()


@blueprint.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie, Authorization, X-CE-View-As"
    return response


@blueprint.errorhandler(ContractViolation)
def violation(exc):
    body, status = public_error(exc)
    return jsonify(body), status


@blueprint.errorhandler(BadRequest)
def malformed(exc):
    return {"error": {"code": "SCHEMA_INVALID"}}, 400


@blueprint.errorhandler(RequestEntityTooLarge)
def oversized(exc):
    return {"error": {"code": "PAYLOAD_TOO_LARGE"}}, 413


@blueprint.errorhandler(Exception)
def unexpected(exc):
    if isinstance(exc, (JWTExtendedException, PyJWTError)):
        return {"error": {"code": "OPERATION_FORBIDDEN"}}, 401
    if isinstance(exc, HTTPException):
        return {"error": {"code": "SCHEMA_INVALID"}}, exc.code
    # No raw exception text, source values, paths or request bodies in telemetry.
    current_app.logger.error("Creation Engine request failure: %s", type(exc).__name__)
    return {"error": {"code": "ENGINE_UNAVAILABLE"}}, 503


def view_id():
    return request.headers.get("X-CE-View-As")


@blueprint.post("/commands")
def commands():
    service = gateway()
    raw = request.stream.read(service.kernel.max_request_bytes + 1)
    service = command_gateway(raw)
    result = service.submit(principal(), raw, view_id=view_id())
    status = {"accepted": 202, "committed": 200, "suspended": 503, "rejected": 409}[result["status"]]
    return jsonify(result), status


@blueprint.get("/scopes/<scope_id>/objects/<object_id>")
def read(scope_id, object_id):
    return jsonify(gateway().read(principal(), scope_id, object_id, operation=request.args.get("operation", "read"), view_id=view_id()))


@blueprint.get("/scopes/<scope_id>/search")
def search(scope_id):
    return jsonify(gateway().search(principal(), scope_id, request.args.get("q", ""), view_id=view_id()))


@blueprint.get("/scopes/<scope_id>/receipts/<key>")
def receipt(scope_id, key):
    return jsonify(gateway().receipt(principal(), scope_id, key, view_id=view_id()))


@blueprint.get("/scopes/<scope_id>/decisions/<decision_id>")
def decision(scope_id, decision_id):
    return jsonify(gateway().decision(principal(), scope_id, decision_id, view_id=view_id()))


@blueprint.get("/scopes/<scope_id>/actions/<action_id>/outcome")
def outcome(scope_id, action_id):
    return jsonify(gateway().outcome(principal(), scope_id, action_id, view_id=view_id(), operation=request.args.get("operation", "read")))


@blueprint.post("/scopes/<scope_id>/view-as")
def enter_view(scope_id):
    if view_id() is not None:
        refuse("OPERATION_FORBIDDEN")
    body = exact_object(request.get_json(), ("memberId",))
    if type(body["memberId"]) is not int:
        refuse("SCHEMA_INVALID")
    return jsonify(gateway().enter_view(principal(), scope_id, body["memberId"])), 201


@blueprint.delete("/scopes/<scope_id>/view-as/<session_id>")
def exit_view(scope_id, session_id):
    return jsonify(gateway().exit_view(principal(), scope_id, session_id))


@blueprint.get("/migration/characters/<int:character_id>/preview")
def migration_preview(character_id):
    from sqlalchemy import select
    from vtt.creation_engine.store.migration_models import CeMigrationLedger
    service = gateway()
    if not hasattr(service.kernel, "migration"):
        refuse("NOT_FOUND")
    with service.store.engine.connect() as connection:
        scope_id = connection.scalar(select(CeMigrationLedger.scope_id).where(
            CeMigrationLedger.source_type == "vtt.character", CeMigrationLedger.source_id == character_id))
    if scope_id is None:
        refuse("NOT_FOUND")
    return jsonify(service.kernel.migration.preview(principal(), scope_id, character_id=character_id))


@blueprint.get("/migration/tokens/<int:token_id>/projection")
def token_projection(token_id):
    service = current_app.extensions.get("ce_legacy")
    if service is None:
        refuse("ENGINE_UNAVAILABLE")
    result = service.read(principal(), "vtt.token", token_id, view_id=view_id())
    if result is None:
        refuse("NOT_FOUND")
    return jsonify(result)
