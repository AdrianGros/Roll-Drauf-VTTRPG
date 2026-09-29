"""Versioned authoring registrations, independent of the runtime host's lock."""

from functools import lru_cache

from vtt.creation_engine.content import SchemaRegistry, SchemaType
from vtt.creation_engine.kernel.records import refuse
from . import flame, manual, race, homebrew

OPERATIONS = frozenset({"CreateDraft", "RecordDraftDecision", "SkipDraftQuestion", "RetractDraftDecision",
                        "ApplyDraftPreset", "RevertDraft", "CommitDraftRevision"})
QUALITIES = ("lore_only", "sheet_ready", "runtime_ready", "automation_complete")
SCHEMA_TYPES = (flame.ITEM_TYPE, *manual.TYPES, race.RACE_TYPE, *homebrew.TYPES)


def guide_for(schema_type):
    if schema_type in homebrew.TYPES:
        return homebrew.interview(schema_type)
    if schema_type == race.RACE_TYPE:
        return race.interview()
    if schema_type in manual.TYPES:
        return manual.interview(schema_type)
    if schema_type != flame.ITEM_TYPE:
        refuse("AUTHORING_REGISTRY_MISMATCH")
    return flame.interview()


@lru_cache(maxsize=3)
def _homebrew_registry(schema_type):
    # SchemaRegistry snapshots inputs and returns defensive copies. These three
    # immutable registrations need not recompile their nested schemas per answer.
    guide = homebrew.interview(schema_type)
    schema = {**homebrew.content_schema(schema_type), "x-authoring": guide.artifact()}
    types = [SchemaType(schema_type.type_id, schema_type.version, schema)]
    types.extend(SchemaType(q.answer_type, q.version, q.schema) for q in guide.questions if q.answer_type)
    return SchemaRegistry(schema_type.type_id + ".authoring", "1", types)


def registry(schema_type=flame.ITEM_TYPE):
    if schema_type in homebrew.TYPES:
        return _homebrew_registry(schema_type)
    if schema_type == race.RACE_TYPE:
        guide = race.interview()
        schema = {**race.content_schema(), "x-authoring": guide.artifact()}
        types = [SchemaType(schema_type.type_id, schema_type.version, schema)]
        types.extend(SchemaType(q.answer_type, q.version, q.schema) for q in guide.questions if q.answer_type)
        return SchemaRegistry(schema_type.type_id + ".authoring", "1", types)
    if schema_type in manual.TYPES:
        guide = manual.interview(schema_type)
        schema = {**manual.content_schema(schema_type), "x-authoring": guide.artifact()}
        types = [SchemaType(schema_type.type_id, schema_type.version, schema)]
        types.extend(SchemaType(q.answer_type, q.version, q.schema) for q in guide.questions if q.answer_type)
        return SchemaRegistry(schema_type.type_id + ".authoring", "1", types)
    if schema_type != flame.ITEM_TYPE:
        refuse("AUTHORING_REGISTRY_MISMATCH")
    guide = flame.interview()
    schema = {**flame.content_schema(), "x-authoring": guide.artifact(),
              "x-presets": [flame.preset(key) for key in ("g1.harmless-flames", "g1.post-hit-flames")]}
    types = [SchemaType(flame.ITEM_TYPE.type_id, flame.ITEM_TYPE.version, schema)]
    answers = {}
    for q in guide.questions:
        if q.answer_type:
            key = (q.answer_type, q.version)
            if key in answers and answers[key] != q.schema:
                raise ValueError("answer schema IDs must have one meaning")
            answers[key] = q.schema
    types.extend(SchemaType(key[0], key[1], value) for key, value in answers.items())
    return SchemaRegistry("g1.authoring-schemas", "1", types)


def quality_gates(state, quality):
    if quality not in QUALITIES:
        refuse("SCHEMA_INVALID")
    for schema_type in homebrew.TYPES:
        if state["compilerVersion"] == homebrew.compiler_version(schema_type):
            return homebrew.quality_gates(schema_type, state, quality)
    if state["compilerVersion"] == race.COMPILER_VERSION:
        return race.quality_gates(state, quality)
    if state["compilerVersion"] == flame.COMPILER_VERSION:
        return flame.quality_gates(state, quality)
    for schema_type in manual.TYPES:
        if state["compilerVersion"] == manual.interview(schema_type).compiler_version:
            return manual.quality_gates(schema_type, state, quality)
    refuse("AUTHORING_REGISTRY_MISMATCH")
