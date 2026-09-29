"""D&D 5e homebrew races for character sheets, with explicitly manual rules.

Race revisions retain author decisions and edition identity. Trait prose, usage,
choices and prerequisites are never interpreted as executable engine mechanics.
"""

from vtt.creation_engine.content import SchemaTypeRef
from .flame import integer, object_schema, text
from .interview import Interview, Question

RACE_TYPE = SchemaTypeRef("dnd5e.authored-race", 1)
COMPILER_VERSION = "dnd5e.race-compiler:1"
EDITIONS = ("dnd5e_2014", "dnd5e_2024")
SIZES = ("tiny", "small", "medium", "large", "huge", "gargantuan", "small_or_medium")
TEXT = {"type": "string", "minLength": 1, "maxLength": 2048, "pattern": r"\S"}
TRAIT_SCHEMA = object_schema({
    "name": {**TEXT, "maxLength": 200},
    "kind": {"enum": ["trait", "feature"]},
    "description": TEXT,
    "usage": TEXT,
    "choices": TEXT,
    "prerequisites": TEXT,
}, required=["name", "kind", "description", "usage"])
TRAITS_SCHEMA = {"type": "array", "minItems": 1, "maxItems": 20, "items": TRAIT_SCHEMA}


def interview():
    return Interview((
        Question("content.name", ("name",), {**TEXT, "maxLength": 50},
            text("Name des Volkes", "Race name", "Nom du peuple",
                 "Wähle einen Namen für das Volk auf dem Charakterbogen.",
                 "Choose the race name shown on the character sheet.",
                 "Choisissez le nom du peuple affiché sur la fiche de personnage."), priority=100),
        Question("race.edition", ("race", "edition"), {"enum": list(EDITIONS)},
            text("D&D-5e-Ausgabe", "D&D 5e edition", "Édition de D&D 5e",
                 "Wähle 2014 oder 2024 ausdrücklich. Ein Wechsel erfordert eine erneute Prüfung der Volksregeln.",
                 "Choose 2014 or 2024 explicitly. Changing edition requires reviewing the race rules again.",
                 "Choisissez explicitement 2014 ou 2024. Un changement exige de revoir les règles du peuple."), priority=90),
        Question("race.creatureType", ("race", "creatureType"), {**TEXT, "maxLength": 100},
            text("Kreaturentyp", "Creature type", "Type de créature",
                 "Gib den Kreaturentyp ausdrücklich an; er wird nicht aus dem Namen abgeleitet.",
                 "Specify the creature type; it is not inferred from the name.",
                 "Précisez le type de créature ; il n'est pas déduit du nom."),
            dependencies=("race.edition",), priority=80),
        Question("race.size", ("race", "size"), {"enum": list(SIZES)},
            text("Größenkategorie", "Size category", "Catégorie de taille",
                 "Wähle eine Größe oder die ausdrückliche Wahl zwischen Klein und Mittel.",
                 "Choose a size or an explicit choice between Small and Medium.",
                 "Choisissez une taille ou un choix explicite entre Petite et Moyenne."),
            dependencies=("race.edition",), priority=70),
        Question("race.speed", ("race", "speed"), integer(0, 300),
            text("Bewegungsrate in Fuß", "Walking speed in feet", "Vitesse de marche en pieds",
                 "Gib eine ganze Zahl zwischen 0 und 300 an. Andere Bewegungsarten kannst du als Merkmal beschreiben.",
                 "Enter an integer from 0 to 300. Describe other movement modes as traits.",
                 "Indiquez un entier de 0 à 300. Décrivez les autres déplacements comme des traits."),
            kind="structured", answer_type="dnd5e.race.answer.speed", dependencies=("race.edition",), priority=60),
        Question("race.languages", ("race", "languages"), TEXT,
            text("Sprachen", "Languages", "Langues",
                 "Nenne die Sprachen oder schreibe ausdrücklich, dass das Volk keine Sprachen verleiht.",
                 "Name the languages or explicitly state that the race grants no languages.",
                 "Nommez les langues ou indiquez explicitement que le peuple n'en accorde aucune."),
            dependencies=("race.edition",), priority=50),
        Question("race.traits", ("race", "traits"), TRAITS_SCHEMA,
            text("Volksmerkmale und Fähigkeiten", "Traits and features", "Traits et capacités",
                 "Lege 1 bis 20 eindeutig benannte Merkmale an. Beschreibe Wirkung, Nutzung, Auswahl und Voraussetzungen; Regeln werden manuell angewendet.",
                 "Add 1 to 20 distinctly named traits or features. Describe effects, usage, choices and prerequisites; rules are applied manually.",
                 "Ajoutez 1 à 20 traits ou capacités aux noms distincts. Décrivez effets, utilisation, choix et prérequis ; les règles sont appliquées manuellement."),
            kind="structured", answer_type="dnd5e.race.answer.traits", dependencies=("race.edition",), priority=40),
        Question("race.abilityScoreRules", ("race", "abilityScoreRules"), TEXT,
            text("Attributsregeln (optional)", "Ability score rules (optional)", "Règles de caractéristiques (facultatif)",
                 "Beschreibe eigene Attributsregeln. Bestehende oder importierte Werte werden dadurch nicht automatisch verändert.",
                 "Describe your ability score rules. Existing or imported scores are not changed automatically.",
                 "Décrivez vos règles de caractéristiques. Les valeurs existantes ou importées ne sont pas modifiées automatiquement."),
            required=False, dependencies=("race.edition",), priority=10),
        Question("content.prose", ("prose",), {**TEXT, "maxLength": 8192},
            text("Beschreibung (optional)", "Description (optional)", "Description (facultatif)",
                 "Beschreibe Aussehen, Herkunft oder Kultur. Aus diesem Text entstehen keine Regeln.",
                 "Describe appearance, origins or culture. This text does not create mechanics.",
                 "Décrivez l'apparence, les origines ou la culture. Ce texte ne crée aucune mécanique."), required=False),
    ), compiler_version=COMPILER_VERSION)


def content_schema():
    properties = {}
    for question in interview().questions:
        parent = properties
        for key in question.path[:-1]:
            parent = parent.setdefault(key, object_schema({}, required=[]))["properties"]
        parent[question.path[-1]] = question.schema
    return object_schema(properties, required=["name"])


def quality_gates(state, quality):
    guide = interview()
    content = guide.values(state)
    required = [guide.by_id["content.name"]] if quality == "lore_only" else [
        question for question in guide.questions if question.required]
    gates = [{"path": list(question.path), "code": "ANSWER_REQUIRED", "questionId": question.id}
             for question in required if question.id not in state["answers"]]
    if quality != "lore_only":
        names = set()
        for index, trait in enumerate(content.get("race", {}).get("traits", [])):
            name = trait["name"].strip().casefold()
            if name in names:
                gates.append({"path": ["race", "traits", str(index), "name"],
                              "code": "TRAIT_NAME_DUPLICATE", "questionId": "race.traits"})
            names.add(name)
        if quality in {"runtime_ready", "automation_complete"}:
            gates.append({"path": [], "code": "MANUAL_PROFILE_ONLY"})
    return gates
