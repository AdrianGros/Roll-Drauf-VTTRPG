"""Versioned VTT D&D JSON transport; imported rule text never executes effects."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import math

from flask import current_app, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from vtt.creation_engine.compiler import catalog, race
from vtt.creation_engine.compiler.interview import StrictValidator
from vtt.creation_engine.errors import ContractViolation
from vtt.extensions import db
from vtt.models import Character, Equipment, InventoryItem, Spell, User

KIND = 'dnd5e_character'
VERSION = 1
MAX_BYTES = 512 * 1024
SCORES = ('str', 'dex', 'con', 'int', 'wis', 'cha')
STATS = (*SCORES, 'level', 'xp', 'ac', 'hp_current', 'hp_max', 'mana_current', 'mana_max', 'proficiency_bonus')
RESERVED_METADATA = {'system_id', 'roll_drauf_light', 'homebrew_origin', 'creation_engine', 'provenance',
                     'workspaceId', 'draftId', 'revisionId', 'definitionId', 'scopeId', 'executionLockDigest'}
REFERENCE_KINDS = {'revision', 'definition', 'instance', 'scope', 'draft', 'workspace'}


class PortableError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def text_field(maximum, *, optional=False):
    field = {'type': 'string', 'maxLength': maximum}
    if optional:
        field['type'] = ['string', 'null']
    else:
        field.update(minLength=1, pattern=r'\S')
    return field


def integer(minimum, maximum):
    return {'type': 'integer', 'minimum': minimum, 'maximum': maximum}


def object_schema(properties, required):
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}


WEIGHT = {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1000000}
BOOLEAN = {'type': 'boolean'}
JSON_OBJECT = {'type': 'object'}
# Wire names match existing resource serializers. Extra descriptive data is explicit.
RESOURCE_FIELDS = {
    'spells': (Spell, {
        'name': text_field(100), 'level': integer(0, 9), 'school': text_field(50, optional=True),
        'casting_time': text_field(50, optional=True), 'range': text_field(50, optional=True),
        'duration': text_field(100, optional=True), 'is_prepared': BOOLEAN, 'is_ritual': BOOLEAN,
        'description': text_field(8192, optional=True), 'damage_dice': text_field(20, optional=True),
        'damage_type': text_field(50, optional=True), 'custom_data': JSON_OBJECT,
    }, {'range': 'range_distance'}),
    'equipment': (Equipment, {
        'name': text_field(100), 'type': text_field(50, optional=True), 'rarity': text_field(50, optional=True),
        'ac_bonus': integer(-100, 100), 'damage_dice': text_field(20, optional=True),
        'damage_type': text_field(50, optional=True), 'is_equipped': BOOLEAN, 'is_cursed': BOOLEAN,
        'weight': WEIGHT, 'cost': text_field(50, optional=True), 'description': text_field(8192, optional=True),
        'special_properties': JSON_OBJECT,
    }, {'type': 'equipment_type'}),
    'inventory': (InventoryItem, {
        'name': text_field(100), 'type': text_field(50, optional=True), 'quantity': integer(0, 1000000),
        'weight_per_unit': WEIGHT, 'cost': text_field(50, optional=True), 'is_consumable': BOOLEAN,
        'is_cursed': BOOLEAN, 'description': text_field(8192, optional=True), 'effects': JSON_OBJECT,
    }, {'type': 'item_type'}),
}


def payload_schema():
    stats = {key: integer(1, 30) for key in SCORES}
    stats.update(level=integer(1, 20), xp=integer(0, 1000000000), ac=integer(0, 100),
                 hp_current=integer(0, 10000), hp_max=integer(1, 10000),
                 mana_current=integer(0, 10000), mana_max=integer(0, 10000),
                 proficiency_bonus=integer(0, 100))
    guide = race.interview()
    origin = object_schema({q.path[-1]: q.schema for q in guide.questions},
                           [q.path[-1] for q in guide.questions if q.required])
    properties = {
        'export_kind': {'const': KIND}, 'export_version': {'const': VERSION, 'type': 'integer'},
        'system_id': {'enum': list(race.EDITIONS)}, 'name': text_field(100), 'race': text_field(50),
        'class': text_field(50), 'background': text_field(100),
        'stats': object_schema(stats, [key for key in STATS if not key.startswith('mana_')]),
        'character_data': JSON_OBJECT, 'homebrew_origin': origin,
    }
    for name, (_, fields, _) in RESOURCE_FIELDS.items():
        properties[name] = {'type': 'array', 'maxItems': 200, 'items': object_schema(fields, ['name'])}
    return object_schema(properties, ['export_kind', 'export_version', 'system_id', 'name', 'race', 'class', 'background', 'stats'])


def _check_metadata(value, path, depth=0):
    if depth > 8:
        raise PortableError(f'{path}: JSON nesting exceeds 8 levels.')
    if isinstance(value, dict):
        if len(value) > 100:
            raise PortableError(f'{path}: at most 100 object fields are supported.')
        if isinstance(value.get('kind'), str) and value['kind'] in REFERENCE_KINDS:
            raise PortableError(f'{path}: engine references are not portable character data.')
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 100 or key in RESERVED_METADATA or key.lower().startswith('ce_'):
                raise PortableError(f'{path}: reserved or unsupported metadata key.')
            _check_metadata(child, f'{path}.{key}', depth + 1)
    elif isinstance(value, list):
        if len(value) > 200:
            raise PortableError(f'{path}: at most 200 array entries are supported.')
        for child in value:
            _check_metadata(child, path, depth + 1)
    elif isinstance(value, str):
        if len(value) > 8192:
            raise PortableError(f'{path}: text exceeds 8192 characters.')
    elif type(value) in (float, int):
        if abs(value) > 1000000000 or not math.isfinite(value):
            raise PortableError(f'{path}: number is outside the portable range.')
    elif value is not None and type(value) is not bool:
        raise PortableError(f'{path}: unsupported JSON value.')


def validate_payload(payload, *, principal):
    try:
        encoded = json.dumps(payload, allow_nan=False, ensure_ascii=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError):
        raise PortableError('D&D import must contain finite, valid JSON.') from None
    if len(encoded) > MAX_BYTES:
        raise PortableError('D&D import exceeds the 512 KiB portable limit.', 413)
    error = next(StrictValidator(payload_schema()).iter_errors(payload), None)
    if error:
        path = '.'.join(str(part) for part in error.absolute_path) or 'payload'
        # Report the field and rule, never echo arbitrary imported values.
        raise PortableError(f'Invalid D&D portable field {path} ({error.validator}).')
    stats = payload['stats']
    if stats['hp_current'] > stats['hp_max'] or stats.get('mana_current', 0) > stats.get('mana_max', 0):
        raise PortableError('Current HP and mana must not exceed their maximum values.')
    _check_metadata(payload.get('character_data', {}), 'character_data')
    for group in RESOURCE_FIELDS:
        for item in payload.get(group, []):
            for key in ('custom_data', 'special_properties', 'effects'):
                if key in item:
                    _check_metadata(item[key], f'{group}.{key}')
    origin = payload.get('homebrew_origin')
    if origin is None:
        return None
    if origin['edition'] != payload['system_id'] or origin['name'] != payload['race']:
        raise PortableError('Homebrew race name and edition must match the character.')
    guide = race.interview()
    state = guide.empty()
    try:
        for question in guide.questions:
            if question.path[-1] in origin:
                state, _, _ = guide.change(state, {'questionId': question.id, 'questionVersion': question.version},
                    answer=question.answer(origin[question.path[-1]]), author=principal, locale='en')
        gates = catalog.quality_gates(state, 'sheet_ready')
    except ContractViolation:
        raise PortableError('Homebrew race rules failed validation.') from None
    if gates:
        raise PortableError('Homebrew race needs complete rules and distinct trait names before import.')
    return guide.values(state)


def export_payload(character):
    from vtt.ce_compat import character_projection, homebrew_origin
    if request.headers.get('X-CE-View-As') is not None:
        raise PortableError('Exit View As before exporting a D&D character.', 403)
    # A direct/lightweight host may not install the legacy HTTP interceptor.
    # Respect its export policy and never serialize stale legacy runtime fields.
    if character_projection(character, operation='export') is not None:
        raise PortableError('Portable D&D export is unavailable for a character managed by the runtime engine.', 409)
    if character.character_data is not None and not isinstance(character.character_data, dict):
        raise PortableError('Existing character_data must be an object before portable export.')
    data = character.character_data or {}
    origin = homebrew_origin(character)
    edition = origin['edition'] if origin else data.get('system_id')
    if edition not in race.EDITIONS or data.get('roll_drauf_light'):
        raise PortableError('This character has no supported, explicit D&D 5e edition.')
    payload = {'export_kind': KIND, 'export_version': VERSION, 'system_id': edition,
               'name': character.name, 'race': origin['name'] if origin else character.race,
               'class': character.class_name, 'background': character.background,
               'stats': {key: getattr(character, key + '_score' if key in SCORES else key) for key in STATS},
               'character_data': {key: deepcopy(value) for key, value in data.items() if key != 'system_id'}}
    for group, (_, fields, aliases) in RESOURCE_FIELDS.items():
        payload[group] = [{key: deepcopy(getattr(item, aliases.get(key, key))) for key in fields}
                          for item in getattr(character, group)]
    if origin:
        payload['homebrew_origin'] = origin
    validate_payload(payload, principal=character.user_id)
    return payload


def import_payload(payload, user):
    content = validate_payload(payload, principal=user.id)
    if request.headers.get('X-CE-View-As') is not None:
        raise PortableError('Exit View As before importing a character.', 403)
    # Hold current account authority until the single import transaction commits.
    user = db.session.scalar(select(User).where(User.id == user.id).with_for_update(read=True)
                             .execution_options(populate_existing=True))
    if user is None or not user.is_active or user.is_suspended or user.account_state != 'active':
        raise PortableError('An active account is required to import a D&D character.', 403)
    if content is not None:
        host = current_app.extensions.get('ce_gateway')
        if not current_app.config.get('CE_AUTHORING') or getattr(host, 'authoring', None) is None:
            raise PortableError('Importing homebrew race rules requires the Creation Engine to be available.', 409)
    stats = payload['stats']
    character = Character(user_id=user.id, campaign_id=None, name=payload['name'], race=payload['race'],
                          class_name=payload['class'], background=payload['background'],
                          character_data={**deepcopy(payload.get('character_data', {})), 'system_id': payload['system_id']},
                          **{key + '_score' if key in SCORES else key: stats.get(key, 0) for key in STATS})
    try:
        db.session.add(character)
        db.session.flush()
        for group, (model, _, aliases) in RESOURCE_FIELDS.items():
            for item in payload.get(group, []):
                db.session.add(model(character_id=character.id,
                                     **{aliases.get(key, key): deepcopy(value) for key, value in item.items()}))
        if content is not None:
            from vtt.creation_engine.content import create_revision
            from vtt.creation_engine.store.content import ContentStore
            from vtt.creation_engine.store.sheet_models import CeCharacterOrigin
            now = datetime.now(timezone.utc)
            store = ContentStore(db.session)
            workspace = store.workspace_for(user.id, now=now)
            definition = store.add_definition(workspace.id, content['name'], race.RACE_TYPE.type_id, now=now)
            registry = catalog.registry(race.RACE_TYPE)
            revision = create_revision(definition.id, race.RACE_TYPE, content, registry=registry,
                author_user_id=user.id, now=now,
                provenance={'kind': 'portable_import', 'sourceFormat': f'{KIND}:{VERSION}',
                            'declaredQuality': 'sheet_ready', 'compilerVersion': race.COMPILER_VERSION,
                            'registry': registry.artifact()})
            store.append_revision(revision)
            db.session.add(CeCharacterOrigin(character_id=character.id, revision_id=revision.id, version=1))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise PortableError('D&D import could not be saved. No character was imported.', 503) from None
    except Exception:
        db.session.rollback()
        raise
    return character
