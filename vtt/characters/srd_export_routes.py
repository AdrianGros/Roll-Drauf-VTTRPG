"""P12 endpoints on the SRD creator blueprint: JSON export/import, printable PDF and the sheet colour theme."""

import json

from flask import Response, jsonify, make_response, request
from flask_jwt_extended import jwt_required

from vtt.characters import srd_export, srd_manage, srd_pdf
from vtt.characters.routes import _can_read_character, _get_character_or_404, _get_current_user
from vtt.characters.srd_creator import _bad, _body, srd_creator_bp
from vtt.characters.srd_progression import ProgressionError
from vtt.characters.sheet_link import srd_evaluation
from vtt.extensions import db, limiter


def _character(char_id, *, owner):
    user, error = _get_current_user()
    if error:
        return None, None, error
    char, error = _get_character_or_404(char_id)
    if error:
        return None, None, error
    if owner and char.user_id != user.id:
        return None, None, _bad('forbidden', 'Nur die Besitzerin oder der Besitzer darf das.', 403)
    if not owner and not _can_read_character(user.id, char):
        return None, None, _bad('forbidden', 'Kein Zugriff.', 403)
    if srd_evaluation(char) is None:
        return None, None, _bad('not_srd', 'Kein SRD-Charakter.', 422)
    return user, char, None


def _private_download(response, name):
    response.headers['Content-Disposition'] = f'attachment; filename="{name}"'
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@srd_creator_bp.get('/characters/<int:char_id>/export')
@limiter.limit('60 per hour')
@jwt_required()
def export_character(char_id):
    _, char, error = _character(char_id, owner=True)
    if error:
        return error
    text = json.dumps(srd_export.export_document(char), ensure_ascii=False, indent=2)
    return _private_download(Response(text, mimetype='application/json'), srd_export.file_name(char))


@srd_creator_bp.get('/characters/<int:char_id>/pdf')
@limiter.limit('60 per hour')
@jwt_required()
def character_pdf(char_id):
    user, char, error = _character(char_id, owner=False)
    if error:
        return error
    content = srd_pdf.render_pdf(char, private=char.user_id == user.id)
    name = srd_export.file_name(char).replace('.rollcharakter.json', '.pdf')
    return _private_download(Response(content, mimetype='application/pdf'), name)


@srd_creator_bp.post('/characters/import')
@limiter.limit('20 per hour')
@jwt_required()
def import_character():
    user, error = _get_current_user()
    if error:
        return error
    if (request.content_length or 0) > srd_export.MAX_BYTES:
        return _bad('too_large', 'Die Datei ist zu groß.', 413)
    body = _body()
    if body is None:
        return _bad('invalid_body', 'Die Datei ist keine gültige JSON-Datei.')
    try:
        char, extras = srd_export.import_character(body, user_id=user.id)
        db.session.add(char)
        db.session.flush()
        srd_export.finish_import(char, extras, user_id=user.id)
        db.session.commit()
    except ProgressionError as exc:
        db.session.rollback()
        extra = exc.extra if exc.code == 'import_invalid' else {}
        return _bad('import_invalid', exc.message, exc.status, **extra)
    except Exception as exc:  # inventory/companion helpers raise their own typed errors
        db.session.rollback()
        code, message = getattr(exc, 'code', None), getattr(exc, 'message', None)
        if code and message:
            return _bad('import_invalid', message, 422)
        raise
    return make_response(jsonify({'character': char.serialize(include_details=True)}), 201)


@srd_creator_bp.get('/characters/<int:char_id>/appearance')
@jwt_required()
def get_appearance(char_id):
    user, char, error = _character(char_id, owner=False)
    if error:
        return error
    return jsonify({'theme': srd_manage.theme_of(char), 'themes': list(srd_manage.THEMES), 'canEdit': char.user_id == user.id})


@srd_creator_bp.put('/characters/<int:char_id>/appearance')
@limiter.limit('120 per hour')
@jwt_required()
def put_appearance(char_id):
    _, char, error = _character(char_id, owner=True)
    if error:
        return error
    body = _body()
    if body is None:
        return _bad('invalid_body', 'JSON-Objekt erwartet.')
    try:
        theme = srd_manage.set_theme(char, body.get('theme'))
        db.session.commit()
    except ProgressionError as exc:
        db.session.rollback()
        return _bad(exc.code, exc.message, exc.status, **exc.extra)
    return jsonify({'theme': theme, 'themes': list(srd_manage.THEMES), 'canEdit': True})
