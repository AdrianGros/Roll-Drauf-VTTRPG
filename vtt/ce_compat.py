"""Optional Creation Engine host lookup; importing this module loads no engine code."""

from flask import current_app, has_app_context, has_request_context


def adapter():
    return current_app.extensions.get("ce_legacy") if has_app_context() else None


def character_projection(character, *, operation="read"):
    service = adapter()
    if service is None or service.representation("vtt.character", character.id) is None:
        return None
    from flask_jwt_extended import get_jwt_identity
    from vtt.creation_engine.kernel.records import refuse
    if not has_request_context():
        refuse("OPERATION_FORBIDDEN")
    from flask import request
    request.environ["ce_legacy_projection"] = True
    try:
        principal = int(get_jwt_identity())
    except (RuntimeError, TypeError, ValueError):
        refuse("OPERATION_FORBIDDEN")
    return service.read(principal, "vtt.character", character.id, operation=operation)


def token_reference(token):
    service = adapter()
    return service.representation("vtt.token", token.id) if service is not None else None
