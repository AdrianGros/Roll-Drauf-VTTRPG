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


def homebrew_origin(character):
    """Public pinned race rules survive editor flags and mutable legacy metadata."""
    if not has_app_context():
        return None
    from sqlalchemy import inspect
    if current_app.extensions.get("sqlalchemy") is not None:
        from vtt.extensions import db
        # Ordinary deployments without M79 never query Creation Engine tables.
        if not inspect(db.session.connection()).has_table("ce_character_origins"):
            return None
        from vtt.creation_engine.store.content import ContentStore
        from vtt.creation_engine.store.race_sheets import sheet_content
        from vtt.creation_engine.store.sheet_models import CeCharacterOrigin
        origin = db.session.get(CeCharacterOrigin, character.id)
        return sheet_content(ContentStore(db.session).revision(origin.revision_id)) if origin else None
    # Lightweight CE hosts do not install Flask-SQLAlchemy themselves.
    host = current_app.extensions.get("ce_gateway")
    authoring = getattr(host, "authoring", None)
    if authoring is None or not inspect(authoring.store.engine).has_table("ce_character_origins"):
        return None
    from vtt.creation_engine.store.race_sheets import RaceSheetService
    return RaceSheetService(authoring).projection(character)
