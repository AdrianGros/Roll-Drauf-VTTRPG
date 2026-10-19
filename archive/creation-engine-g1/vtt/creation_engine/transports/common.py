"""Transport error allowlist. Detailed diagnostics stay on the server."""

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity

from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.policy.public_errors import public_error


def principal():
    try:
        value = int(get_jwt_identity())
    except (TypeError, ValueError):
        refuse("OPERATION_FORBIDDEN")
    if value <= 0:
        refuse("OPERATION_FORBIDDEN")
    return value


def gateway(*, mutate=False):
    if mutate and not current_app.config.get("CE_RUNTIME", False):
        refuse("NOT_FOUND")
    if not any(current_app.config.get(flag, False) for flag in ("CE_RUNTIME", "CE_AUTHORING", "CE_SHADOW")):
        refuse("NOT_FOUND")
    value = current_app.extensions.get("ce_gateway")
    if value is None:
        refuse("ENGINE_UNAVAILABLE")
    return value


def exact_object(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        refuse("SCHEMA_INVALID")
    return value


def command_gateway(raw):
    from vtt.creation_engine.kernel.records import Command
    from vtt.creation_engine.compiler.catalog import OPERATIONS as AUTHORING_OPERATIONS
    service = gateway()
    command = Command.parse(raw, max_bytes=service.kernel.max_request_bytes)
    if command.wire["operation"] in AUTHORING_OPERATIONS or command.wire["operation"] == "CreateSandboxScope":
        if not current_app.config.get("CE_AUTHORING"):
            refuse("NOT_FOUND")
        if not hasattr(service, "authoring"):
            refuse("ENGINE_UNAVAILABLE")
        return service
    shadow_commands = {"OpenLegacyCampaignScope", "MapLegacyCharacter", "BeginScopeShadow", "ApproveParityDifference"}
    if not current_app.config.get("CE_RUNTIME") and not (
            current_app.config.get("CE_SHADOW") and command.wire["operation"] in shadow_commands):
        refuse("NOT_FOUND")
    return service


def authoring():
    service = gateway()
    if not current_app.config.get("CE_AUTHORING"):
        refuse("NOT_FOUND")
    if not hasattr(service, "authoring"):
        refuse("ENGINE_UNAVAILABLE")
    return service.authoring


def authoring_available(user):
    """Display capability only; authoring endpoints recheck current authority.

    Reading the dashboard must not provision a workspace or depend on a role
    name. Match the authoring service's usable-account conditions without
    reading or exposing any draft content.
    """
    host = current_app.extensions.get("ce_gateway")
    return bool(current_app.config.get("CE_AUTHORING")
                and getattr(host, "authoring", None) is not None
                and not request.headers.get("X-CE-View-As")
                and user is not None and user.is_active
                and not user.is_suspended and user.account_state == "active")
