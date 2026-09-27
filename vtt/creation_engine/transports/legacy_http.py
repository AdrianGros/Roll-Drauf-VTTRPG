"""Authenticated legacy route interception, installed only by the RDL host."""

from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request

from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.policy.public_errors import public_error
from vtt.creation_engine.transports.common import principal
from vtt.extensions import db


def context_from_headers():
    result = {"idempotencyKey": request.headers.get("Idempotency-Key")}
    for key, header in (("authorityEpoch", "X-CE-Authority-Epoch"), ("expectedScopeVersion", "X-CE-Scope-Version")):
        value = request.headers.get(header)
        if value is not None and value.isascii() and value.isdecimal():
            result[key] = int(value)
    return result


def install_http(app, compatibility):
    def intercept():
        args = request.view_args or {}
        char_id = args.get("char_id")
        if char_id is None or compatibility.representation("vtt.character", char_id) is None:
            return None
        verify_jwt_in_request()
        actor = principal()
        request.environ["ce_legacy_projection"] = True
        if "/identity/" in request.path:
            compatibility.read(actor, "vtt.character", char_id)
            return None
        if request.method == "GET":
            value = compatibility.read(actor, "vtt.character", char_id,
                operation="export" if request.path.endswith("/export") else "read",
                view_id=request.headers.get("X-CE-View-As"))
            suffix = request.path.rsplit("/", 1)[-1]
            if suffix in {"equipment", "inventory", "spells"}:
                # Item metadata is private and inert; return projected occurrences.
                with compatibility.gateway._transaction(value["engine"]["scopeId"]) as tx:
                    audience = compatibility.gateway._audience(tx, actor, request.headers.get("X-CE-View-As"))
                    from sqlalchemy import select
                    from vtt.creation_engine.store.migration_models import CeMigrationLedger
                    from vtt.creation_engine.store.runtime_models import CeInstance
                    ids = tx.session.scalars(select(CeInstance.id).join(CeMigrationLedger, CeMigrationLedger.opaque_id == CeInstance.id)
                        .where(CeInstance.holder_id == value["engine"]["instanceId"], CeMigrationLedger.source_type == "vtt." + suffix))
                    rows = [p for key in ids if (p := compatibility.gateway._project(tx, audience, compatibility.gateway.document(tx, key))) is not None]
                    return jsonify({suffix: rows})
            if suffix == "export":
                return jsonify({"export_kind": "creation_engine_legacy_compat", "export_version": 1, "character": value})
            if suffix == "sheet":
                return jsonify({"character": value, "items": value["items"]})
            return jsonify(value)
        if request.headers.get("X-CE-View-As"):
            refuse("OPERATION_FORBIDDEN")
        if request.method == "PUT" and args.get("item_id") is not None and "/equipment/" in request.path:
            from vtt.models.equipment import Equipment
            item = db.session.get(Equipment, args["item_id"])
            if item is None or item.character_id != char_id:
                refuse("NOT_FOUND")
            kind, source_id = "vtt.equipment", args["item_id"]
        elif request.method == "PUT" and str(char_id) == request.path.rsplit("/", 1)[-1]:
            kind, source_id = "vtt.character", char_id
        else:
            compatibility.read(actor, "vtt.character", char_id)
            refuse("LEGACY_FIELD_READ_ONLY")
        limit = compatibility.gateway.kernel.max_request_bytes
        raw = request.stream.read(limit + 1)
        if len(raw) > limit:
            refuse("PAYLOAD_TOO_LARGE")
        receipt = compatibility.translate(actor, kind, source_id, parse_strict_json(raw), context_from_headers())
        if receipt is None:
            refuse("NOT_FOUND")
        return jsonify({"receipt": receipt, "character": compatibility.read(actor, "vtt.character", char_id)})

    app.before_request(intercept)

    @app.after_request
    def private_projection(response):
        if request.environ.get("ce_legacy_projection"):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["Vary"] = "Cookie, Authorization, X-CE-View-As"
        return response

    from vtt.creation_engine.errors import ContractViolation
    @app.errorhandler(ContractViolation)
    def violation(exc):
        db.session.rollback()
        body, status = public_error(exc)
        return jsonify(body), status
