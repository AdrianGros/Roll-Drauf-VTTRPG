"""Dedicated namespace: cookie JWT + CSRF handshake, no campaign-room broadcasts."""

from functools import wraps
import secrets

from flask import current_app, request, session
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_socketio import emit
from jwt import PyJWTError

from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.kernel.records import refuse
from .common import command_gateway, exact_object, gateway, principal, public_error

NAMESPACE = "/creation-engine"


def register(socketio):
    def authenticated(handler):
        @wraps(handler)
        def wrapped(data=None):
            try:
                verify_jwt_in_request()
                if session.get("ce_authenticated") is not True:
                    refuse("OPERATION_FORBIDDEN")
                return handler(data)
            except ContractViolation as exc:
                body, status = public_error(exc)
                return {**body, "status": status}
            except (JWTExtendedException, PyJWTError):
                return {"error": {"code": "OPERATION_FORBIDDEN"}, "status": 403}
            except Exception as exc:
                current_app.logger.error("Creation Engine socket failure: %s", type(exc).__name__)
                return {"error": {"code": "ENGINE_UNAVAILABLE"}, "status": 503}
        return wrapped

    @socketio.on("connect", namespace=NAMESPACE)
    def connect(auth=None):
        try:
            verify_jwt_in_request()
            gateway()
            expected = get_jwt().get("csrf")
            supplied = auth.get("csrf") if isinstance(auth, dict) else None
            if not isinstance(expected, str) or not isinstance(supplied, str) or not secrets.compare_digest(expected, supplied):
                return False
            session["ce_authenticated"] = True
            return True
        except Exception:
            return False

    @socketio.on("ce:command", namespace=NAMESPACE)
    @authenticated
    def command(data):
        body = exact_object(data, ("command",))
        # Preserve raw envelope text so duplicate keys and invalid JSON numbers
        # reach the same strict parser as REST, before a JSON library loses them.
        if not isinstance(body["command"], str):
            refuse("SCHEMA_INVALID")
        return command_gateway(body["command"]).submit(principal(), body["command"])

    @socketio.on("ce:subscribe", namespace=NAMESPACE)
    @authenticated
    def subscribe(data):
        body = exact_object(data, ("scopeId", "contractVersion", "authorityEpoch"))
        return gateway().subscribe(principal(), body["scopeId"], request.sid,
            contract_version=body["contractVersion"], authority_epoch=body["authorityEpoch"])

    @socketio.on("ce:poll", namespace=NAMESPACE)
    @authenticated
    def poll(data):
        body = exact_object(data, ("scopeId", "subscriptionId", "cursor"))
        return gateway().poll(principal(), body["scopeId"], body["subscriptionId"], body["cursor"], request.sid,
                              deliver=lambda value: emit("ce:events", value, to=request.sid, namespace=NAMESPACE))

    @socketio.on("ce:unsubscribe", namespace=NAMESPACE)
    @authenticated
    def unsubscribe(data):
        body = exact_object(data, ("scopeId",))
        gateway().disconnect(principal(), body["scopeId"], request.sid)
        return {"closed": True}
