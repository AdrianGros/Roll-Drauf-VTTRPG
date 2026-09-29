"""Typed, executable homebrew profiles. Existing G1/race registries stay pinned."""

from functools import lru_cache

from vtt.creation_engine.content import SchemaTypeRef
from .flame import integer, object_schema, text
from .interview import Interview, Question
from .race import EDITIONS

CLASS = SchemaTypeRef("dnd5e.authored-class", 1)
RACE = SchemaTypeRef("dnd5e.runtime-race", 1)
SPELL = SchemaTypeRef("dnd5e.authored-spell", 1)
TYPES = (CLASS, RACE, SPELL)
KINDS = {CLASS: "class", RACE: "race", SPELL: "spell"}
ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
DAMAGE_TYPES = ("acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
                "piercing", "poison", "psychic", "radiant", "slashing", "thunder")
IDENTIFIER = {"type": "string", "pattern": r"^[a-z][a-z0-9_.-]{0,63}$"}
NAME = {"type": "string", "minLength": 1, "maxLength": 200, "pattern": r"\S"}
PROSE = {"type": "string", "maxLength": 8192}


def array(items, maximum=30, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}


MODIFIERS = object_schema({key: integer(-30, 30) for key in (*ABILITIES, "ac", "speed", "hpMax")}, required=[])
RESOURCE = object_schema({"id": IDENTIFIER, "maximum": integer(1, 1000),
                          "recovery": {"enum": ["short_rest", "long_rest", "manual"]}})
GRANTS = object_schema({"modifiers": MODIFIERS, "proficiencies": array(IDENTIFIER),
                       "resistances": array({"enum": list(DAMAGE_TYPES)}),
                       "resources": array(RESOURCE, 12), "spells": array(IDENTIFIER)})
OPTION = object_schema({"id": IDENTIFIER, "name": NAME, "grants": GRANTS})
CHOICE = object_schema({"id": IDENTIFIER, "name": NAME, "count": integer(1, 10),
                       "options": array(OPTION, 20, 1)})
FEATURE = object_schema({"id": IDENTIFIER, "name": NAME, "description": PROSE,
                        "grants": GRANTS, "choices": array(CHOICE, 10)})
LEVEL = object_schema({"level": integer(1, 20), "hpGain": integer(0, 1000),
                      "features": array(FEATURE, 20)})
DICE = object_schema({"count": integer(0, 40), "sides": integer(2, 100), "bonus": integer(0, 1000)})
RESOLUTION = {"oneOf": [object_schema({"kind": {"const": "automatic"}}),
    object_schema({"kind": {"const": "attack"}, "ability": {"enum": list(ABILITIES)}}),
    object_schema({"kind": {"const": "save"}, "ability": {"enum": list(ABILITIES)},
                   "saveAbility": {"enum": list(ABILITIES)}, "halfOnSave": {"type": "boolean"}})]}
EFFECT = {"oneOf": [object_schema({"kind": {"const": "damage"}, "dice": DICE,
                                    "damageType": {"enum": list(DAMAGE_TYPES)}}),
    object_schema({"kind": {"const": "healing"}, "dice": DICE}),
    object_schema({"kind": {"const": "modifier"}, "stat": {"enum": ["ac", "speed"]},
                   "amount": integer(-30, 30)})]}


def compiler_version(schema_type):
    return f"dnd5e.{KINDS[schema_type]}-mechanics:1"


@lru_cache(maxsize=3)
def interview(schema_type):
    kind = KINDS[schema_type]
    def question(key, schema, labels, *, dependencies=(), required=True, priority=0):
        return Question(key, tuple(key.split(".")) if "." in key else (key,), schema,
            text(*labels, "Regeln ausdrücklich festlegen; Freitext erzeugt keine Mechanik.",
                 "Specify rules explicitly; prose creates no mechanics.",
                 "Définissez les règles explicitement ; le texte ne crée aucune mécanique."),
            kind="structured", answer_type=f"{schema_type.type_id}.answer.{key}",
            dependencies=dependencies, required=required, priority=priority)
    qs = [question("name", NAME, ("Name", "Name", "Nom"), priority=100),
          question(f"{kind}.edition", {"enum": list(EDITIONS)}, ("Ausgabe", "Edition", "Édition"), priority=90)]
    if schema_type == CLASS:
        fields = [("hitDie", {"enum": [4, 6, 8, 10, 12, 20]}, ("Trefferwürfel", "Hit die", "Dé de vie")),
                  ("levels", array(LEVEL, 20, 1), ("Stufen und Merkmale", "Levels and features", "Niveaux et capacités"))]
    elif schema_type == RACE:
        fields = [("creatureType", NAME, ("Kreaturentyp", "Creature type", "Type de créature")),
                  ("size", {"enum": ["tiny", "small", "medium", "large", "huge", "gargantuan"]}, ("Größe", "Size", "Taille")),
                  ("speed", integer(0, 300), ("Bewegung in Fuß", "Speed in feet", "Vitesse en pieds")),
                  ("features", array(FEATURE, 20, 1), ("Merkmale", "Features", "Capacités"))]
    else:
        fields = [("key", IDENTIFIER, ("Zauberschlüssel", "Spell key", "Clé du sort")),
                  ("level", integer(0, 9), ("Zaubergrad", "Spell level", "Niveau du sort")),
                  ("school", NAME, ("Schule", "School", "École")),
                  ("castingTime", {"enum": ["action", "bonus_action", "reaction"]}, ("Zauberzeit", "Casting time", "Temps d'incantation")),
                  ("components", NAME, ("Komponenten", "Components", "Composantes")),
                  ("target", {"enum": ["self", "single"]}, ("Ziel", "Target", "Cible")),
                  ("rangeFeet", integer(0, 10000), ("Reichweite in Fuß", "Range in feet", "Portée en pieds")),
                  ("cost", object_schema({"resource": {"oneOf": [IDENTIFIER, {"type": "null"}]}, "amount": integer(0, 1000)}), ("Kosten", "Cost", "Coût")),
                  ("resolution", RESOLUTION, ("Auflösung", "Resolution", "Résolution")),
                  ("effect", EFFECT, ("Wirkung", "Effect", "Effet")),
                  ("durationRounds", integer(0, 10000), ("Dauer in Runden", "Duration in rounds", "Durée en rounds")),
                  ("concentration", {"type": "boolean"}, ("Konzentration", "Concentration", "Concentration")),
                  ("upcast", object_schema({"dicePerLevel": integer(0, 10), "costPerLevel": integer(0, 100)}), ("Höhere Grade", "Higher levels", "Niveaux supérieurs"))]
    qs.extend(question(f"{kind}.{key}", schema, labels, dependencies=(f"{kind}.edition",), priority=50-i)
              for i, (key, schema, labels) in enumerate(fields))
    qs.append(question("prose", PROSE, ("Beschreibung", "Description", "Description"), required=False))
    return Interview(tuple(qs), compiler_version=compiler_version(schema_type))


def content_schema(schema_type):
    properties = {}
    for q in interview(schema_type).questions:
        if len(q.path) == 1:
            properties[q.path[0]] = q.schema
        else:
            properties.setdefault(q.path[0], object_schema({}, required=[]))["properties"][q.path[1]] = q.schema
    return object_schema(properties, required=["name"])


def semantic_errors(schema_type, values):
    kind = KINDS[schema_type]
    body = values[kind]
    errors = []
    if schema_type == SPELL:
        effect, cost, duration = body["effect"], body["cost"], body["durationRounds"]
        if (cost["resource"] is None) != (cost["amount"] == 0):
            errors.append("SPELL_COST_INVALID")
        if (effect["kind"] == "modifier") != (duration > 0):
            errors.append("SPELL_DURATION_INVALID")
        if body["concentration"] and not duration:
            errors.append("SPELL_DURATION_INVALID")
        if effect["kind"] != "damage" and body["resolution"]["kind"] != "automatic":
            errors.append("SPELL_RESOLUTION_INVALID")
        if body["target"] == "self" and body["rangeFeet"] != 0:
            errors.append("SPELL_TARGET_INVALID")
        if (effect["kind"] == "modifier" and body["upcast"]["dicePerLevel"] or
                cost["resource"] is None and body["upcast"]["costPerLevel"]):
            errors.append("SPELL_SCALING_INVALID")
        if "dice" in effect and effect["dice"]["count"] + (9 - body["level"]) * body["upcast"]["dicePerLevel"] > 100:
            errors.append("SPELL_SCALING_INVALID")
        return errors
    if schema_type == CLASS:
        levels = body["levels"]
        if [level["level"] for level in levels] != list(range(1, len(levels)+1)):
            errors.append("CLASS_LEVEL_SEQUENCE_INVALID")
        features = [feature for level in levels for feature in level["features"]]
    else:
        features = body["features"]
    ids = set()
    recoveries = {}
    for feature in features:
        if feature["id"] in ids:
            errors.append("FEATURE_ID_DUPLICATE")
        ids.add(feature["id"])
        choices = set()
        grants = [feature["grants"]]
        for choice in feature["choices"]:
            options = [option["id"] for option in choice["options"]]
            if choice["id"] in choices or len(options) != len(set(options)) or choice["count"] > len(options):
                errors.append("CHOICE_INVALID")
            choices.add(choice["id"])
            grants.extend(option["grants"] for option in choice["options"])
        for grant in grants:
            resource_ids = [resource["id"] for resource in grant["resources"]]
            if len(resource_ids) != len(set(resource_ids)):
                errors.append("GRANT_DUPLICATE")
            for resource in grant["resources"]:
                if resource["id"] in recoveries and recoveries[resource["id"]] != resource["recovery"]:
                    errors.append("RESOURCE_RECOVERY_CONFLICT")
                recoveries[resource["id"]] = resource["recovery"]
            for key in ("proficiencies", "resistances", "spells"):
                if len(grant[key]) != len(set(grant[key])):
                    errors.append("GRANT_DUPLICATE")
    return sorted(set(errors))


def quality_gates(schema_type, state, quality):
    guide = interview(schema_type)
    required = [q for q in guide.questions if q.required and (quality != "lore_only" or q.id == "name")]
    gates = [{"path": list(q.path), "questionId": q.id, "code": "ANSWER_REQUIRED"}
             for q in required if q.id not in state["answers"]]
    if not gates and quality != "lore_only":
        gates.extend({"path": [KINDS[schema_type]], "code": code}
                     for code in semantic_errors(schema_type, guide.values(state)))
    if quality == "automation_complete":
        gates.append({"path": [], "code": "HUMAN_EVENT_ATTESTATION_REQUIRED"})
    return gates
