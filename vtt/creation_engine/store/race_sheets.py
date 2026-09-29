"""Owner-authorized race handoff; no trait execution or imported stat changes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.compiler import race
from vtt.creation_engine.compiler.interview import StrictValidator
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.legacy.guards import legacy_scopes
from vtt.creation_engine.store.models import CeDefinition, CeRevision
from vtt.creation_engine.store.runtime_models import CeRuntimeScope
from vtt.creation_engine.store.sheet_models import CeCharacterOrigin, CeSheetCommand
from vtt.creation_engine.types import RevisionRef, parse_id, parse_reference
from vtt.models import Character

CONTRACT = "race-sheet:1"
CORE_FIELDS = ("name", "class", "background", "level", "ac", "hp_max", "str", "dex", "con", "int", "wis", "cha")


def character_schema():
    properties = {key: {"type": "integer", "minimum": 1, "maximum": 30} for key in ("str", "dex", "con", "int", "wis", "cha")}
    properties.update({
        "name": {"type": "string", "minLength": 1, "maxLength": 100, "pattern": r"\S"},
        "class": {"type": "string", "minLength": 1, "maxLength": 50, "pattern": r"\S"},
        "background": {"type": "string", "minLength": 1, "maxLength": 100, "pattern": r"\S"},
        "level": {"type": "integer", "minimum": 1, "maximum": 20},
        "ac": {"type": "integer", "minimum": 0, "maximum": 100},
        "hp_max": {"type": "integer", "minimum": 1, "maximum": 10000},
    })
    return {"type": "object", "properties": properties, "required": list(CORE_FIELDS), "additionalProperties": False}


def sheet_content(revision):
    values = revision.content
    return {"name": values["name"], **({"prose": values["prose"]} if "prose" in values else {}), **values["race"]}


def system(character, origin, content):
    data = character.character_data or {}
    if not isinstance(data, dict):
        return "unsupported"
    if data.get("roll_drauf_light"):
        return "roll_drauf_light"
    if origin:
        return content.revision(origin.revision_id).content["race"]["edition"]
    declared = data.get("system_id")
    if declared in ("dnd5e_2014", "dnd5e_2024"):
        return declared
    if declared not in (None, "dnd5e"):
        return str(declared)
    return "unassigned"


def character_state(character, origin):
    # Any intervening sheet edit invalidates the reviewed target.
    values = {column.key: getattr(character, column.key) for column in Character.__table__.columns}
    values = {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in values.items()}
    return content_digest({"character": values, "origin": None if origin is None else
        {"revisionId": origin.revision_id, "version": origin.version}})


class RaceSheetService:
    def __init__(self, authoring):
        self.authoring = authoring

    def catalog(self, principal, workspace_id):
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            rows = session.scalars(select(CeRevision).join(CeDefinition).where(
                CeDefinition.workspace_id == workspace_id, CeDefinition.tombstoned_at.is_(None),
                CeRevision.schema_type_id == race.RACE_TYPE.type_id).order_by(CeRevision.created_at, CeRevision.id))
            revisions = []
            for row in rows:
                revision = content.revision(row.id)
                if parse_strict_json(revision.provenance).get("declaredQuality") == "sheet_ready":
                    revisions.append({"revision": revision.ref().to_wire(), "content": sheet_content(revision)})
            characters = []
            for character in session.scalars(select(Character).where(Character.user_id == principal, Character.deleted_at.is_(None)).order_by(Character.name, Character.id)):
                origin = session.get(CeCharacterOrigin, character.id)
                edition = system(character, origin, content)
                if edition not in {"unassigned", "dnd5e_2014", "dnd5e_2024"}:
                    continue
                characters.append({"id": character.id, "name": character.name, "race": character.race,
                    "edition": edition, "expectedState": character_state(character, origin),
                    "origin": sheet_content(content.revision(origin.revision_id)) if origin else None})
            return {"contractVersion": CONTRACT, "revisions": revisions, "characters": characters}

    def _revision(self, content, workspace_id, reference):
        ref = parse_reference(reference, accept=(RevisionRef,))
        revision = content.revision(ref.id)
        definition = content.definition(ref.definition_id)
        if (revision is None or definition is None or definition.workspace_id != workspace_id or
                definition.tombstoned_at or revision.ref() != ref or revision.schema_type != race.RACE_TYPE):
            refuse("NOT_FOUND")
        if parse_strict_json(revision.provenance).get("declaredQuality") != "sheet_ready":
            refuse("RACE_REVISION_REQUIRED")
        return revision

    @staticmethod
    def _guard_target(session, character):
        # Fence no-op replacements too: an ENGINE race is not legacy-owned.
        scope_ids = legacy_scopes(session, character)
        scopes = session.scalars(select(CeRuntimeScope).where(CeRuntimeScope.id.in_(scope_ids)).order_by(CeRuntimeScope.id).with_for_update())
        if any(scope.migration_state not in {"LEGACY", "SHADOW"} for scope in scopes):
            refuse("LEGACY_FIELD_READ_ONLY")

    def apply(self, principal, workspace_id, payload):
        common = {"contractVersion", "idempotencyKey", "revision"}
        if not isinstance(payload, dict) or (set(payload) != common | {"target"} and set(payload) != common | {"character"}):
            refuse("SCHEMA_INVALID")
        if payload["contractVersion"] != CONTRACT:
            refuse("SCHEMA_INVALID")
        key = parse_id(payload["idempotencyKey"])
        digest = content_digest(payload)
        target = payload.get("target")
        if "target" in payload and (not isinstance(target, dict) or set(target) != {"characterId", "expectedState"} or
                type(target["characterId"]) is not int or not isinstance(target["expectedState"], str)):
            refuse("SCHEMA_INVALID")
        if "character" in payload and not StrictValidator(character_schema()).is_valid(payload["character"]):
            refuse("SCHEMA_INVALID")
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            revision = self._revision(content, workspace_id, payload["revision"])
            previous = session.get(CeSheetCommand, (principal, key))
            if previous:
                if previous.request_digest != digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                result = parse_strict_json(previous.result)
                existing = session.get(Character, result["characterId"])
                if existing is None or existing.user_id != principal or existing.deleted_at:
                    refuse("NOT_FOUND")
                return result
            edition = revision.content["race"]["edition"]
            if target is not None:
                character = session.scalar(select(Character).where(Character.id == target["characterId"],
                    Character.user_id == principal, Character.deleted_at.is_(None)).with_for_update())
                if character is None:
                    refuse("NOT_FOUND")
                self._guard_target(session, character)
                origin = session.get(CeCharacterOrigin, character.id)
                if character_state(character, origin) != target["expectedState"]:
                    refuse("CHARACTER_STATE_CONFLICT")
                if system(character, origin, content) not in {"unassigned", edition}:
                    refuse("CHARACTER_SYSTEM_MISMATCH")
            else:
                values = payload["character"]
                character = Character(user_id=principal, name=values["name"], class_name=values["class"],
                    background=values["background"], level=values["level"], ac=values["ac"],
                    hp_current=values["hp_max"], hp_max=values["hp_max"], mana_current=0, mana_max=0,
                    proficiency_bonus=2 + (values["level"] - 1) // 4,
                    **{key + "_score": values[key] for key in ("str", "dex", "con", "int", "wis", "cha")},
                    character_data={"system_id": edition})
                self._guard_target(session, character)
                session.add(character)
                session.flush()
                origin = None
            character.race = revision.content["name"]
            character.character_data = {**(character.character_data or {}), "system_id": edition}
            if origin is None:
                origin = CeCharacterOrigin(character_id=character.id, revision_id=revision.id, version=1)
                session.add(origin)
            elif origin.revision_id != revision.id:
                origin.revision_id = revision.id
                origin.version += 1
            session.flush()
            result = {"characterId": character.id, "href": f"/character-sheet?id={character.id}",
                      "originVersion": origin.version, "revision": revision.ref().to_wire()}
            session.add(CeSheetCommand(principal_id=principal, idempotency_key=key,
                                      request_digest=digest, result=canonical_bytes(result)))
        return result

    def projection(self, character):
        with Session(self.authoring.store.engine) as session:
            origin = session.get(CeCharacterOrigin, character.id)
            if origin is None:
                return None
            return sheet_content(ContentStore(session).revision(origin.revision_id))
