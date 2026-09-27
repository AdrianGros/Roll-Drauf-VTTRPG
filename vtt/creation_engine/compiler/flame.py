"""G1's bounded magic-item interview and reviewed, opt-in presets (§15/T31–32)."""

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.content import SchemaTypeRef
from vtt.creation_engine.kernel.records import refuse
from .interview import Interview, Question, copy

ITEM_TYPE = SchemaTypeRef("g1.authored-magic-item", 1)
COMPILER_VERSION = "g1.flame-compiler:1"


def text(de, en, fr, de_help, en_help, fr_help):
    return {locale: {"label": label, "help": help_text} for locale, label, help_text in
            (("de", de, de_help), ("en", en, en_help), ("fr", fr, fr_help))}


def integer(minimum=0, maximum=1000):
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def object_schema(properties, required=None):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required,
            "additionalProperties": False}


BEHAVIORS = ("visual", "damage", "burst", "transformation", "manual")
MECHANICS = (("flame.behavior", ("visual", "damage")),)
DAMAGE = (("flame.behavior", ("damage",)),)
DICE_SCHEMA = object_schema({"count": integer(1, 100), "sides": integer(2, 1000)})
DURATION_SCHEMA = {"$ref": "urn:rolldrauf:creation-engine:contracts:1.1.3#/$defs/Duration"}


def interview():
    return Interview((
        Question("item.name", ("name",), {"type": "string", "minLength": 1, "maxLength": 200, "pattern": r"\S"},
            text("Wie heißt der Gegenstand?", "What is the item called?", "Comment s'appelle l'objet ?",
                 "Ein Name legt keine Regeln fest.", "A name does not establish mechanics.", "Un nom ne définit aucune mécanique."), priority=100),
        Question("item.prose", ("prose",), {"type": "string", "maxLength": 8192},
            text("Beschreibung", "Description", "Description",
                 "Freitext bleibt Beschreibung; daraus entstehen keine Regeln.", "Free text stays prose; no mechanics are inferred.",
                 "Le texte reste descriptif ; aucune mécanique n'en est déduite."), required=False),
        Question("flame.behavior", ("flames", "behavior"), {"enum": list(BEHAVIORS)},
            text("Was bewirken die Flammen?", "What do the flames do?", "Que font les flammes ?",
                 "Wähle Optik, Zusatzschaden oder eine manuell aufgelöste Wirkung.",
                 "Choose a visual effect, additional damage, or a manually resolved behavior.",
                 "Choisissez un effet visuel, des dégâts supplémentaires ou un comportement résolu manuellement."), priority=1000),
        Question("flame.timing", ("flames", "timing"), {"enum": ["activation", "after_hit"]},
            text("Wann werden die Flammen ausgelöst?", "When do the flames activate?", "Quand les flammes se déclenchent-elles ?",
                 "Aktivierung oder ein bereits bestätigter Treffer; kein Treffer wird erfunden.",
                 "Activation or an already committed hit; no hit is invented.",
                 "À l'activation ou après une touche déjà confirmée ; aucune touche n'est inventée."),
            dependencies=("flame.behavior",), conditions=MECHANICS, priority=90),
        Question("flame.duration", ("flames", "duration"), DURATION_SCHEMA,
            text("Wie lange wirkt die Flamme?", "How long does the flame last?", "Combien de temps dure la flamme ?",
                 "Wähle eine explizite Dauer. Nicht unterstützte Uhren bleiben manuell.",
                 "Choose an explicit duration. Unsupported clocks remain manual.",
                 "Choisissez une durée explicite. Les horloges non prises en charge restent manuelles."),
            kind="structured", answer_type="g1.answer.duration", dependencies=("flame.behavior", "flame.timing"), conditions=MECHANICS, priority=80),
        Question("flame.maximum", ("flames", "maximumCharges"), integer(),
            text("Wie viele Ladungen passen hinein?", "How many charges can it hold?", "Combien de charges peut-il contenir ?",
                 "Die Kapazität wird nicht aus einer Beschreibung geraten.", "Capacity is not guessed from prose.",
                 "La capacité n'est pas déduite du texte."), kind="structured", answer_type="g1.answer.integer",
            dependencies=("flame.behavior",), conditions=MECHANICS, priority=70),
        Question("flame.initial", ("flames", "initialCharges"), integer(),
            text("Mit wie vielen Ladungen beginnt ein neues Exemplar?", "How many charges does a new copy start with?", "Avec combien de charges un nouvel exemplaire commence-t-il ?",
                 "Jedes Exemplar hat einen eigenen Vorrat; maximal die gewählte Kapazität.",
                 "Each copy has its own pool, up to the chosen capacity.",
                 "Chaque exemplaire possède sa propre réserve, limitée à la capacité choisie."), kind="structured", answer_type="g1.answer.integer",
            dependencies=("flame.behavior", "flame.maximum"), conditions=MECHANICS, priority=60),
        Question("flame.cost", ("flames", "cost"), integer(),
            text("Wie viele Ladungen kostet eine Nutzung?", "How many charges does one use cost?", "Combien de charges coûte une utilisation ?",
                 "Auch kostenlos ist eine ausdrückliche Entscheidung.", "Even zero cost is an explicit decision.",
                 "Même un coût nul est une décision explicite."), kind="structured", answer_type="g1.answer.integer",
            dependencies=("flame.behavior", "flame.maximum"), conditions=MECHANICS, priority=50),
        Question("flame.recovery", ("flames", "recovery"), {"enum": ["long_rest", "campaign_dawn", "manual_event"]},
            text("Welches Ereignis füllt die Ladungen auf?", "Which event restores the charges?", "Quel événement restaure les charges ?",
                 "Ein Tag bedeutet nicht automatisch 24 Stunden. Das Ereignis wird im Sandbox-Test ausdrücklich bestätigt.",
                 "A day does not automatically mean 24 hours. The event is explicitly confirmed in the sandbox test.",
                 "Un jour ne signifie pas automatiquement 24 heures. L'événement est confirmé explicitement dans le test bac à sable."),
            dependencies=("flame.behavior", "flame.maximum"), conditions=MECHANICS, priority=40),
        Question("flame.damage", ("flames", "damage"), DICE_SCHEMA,
            text("Wie viel Zusatzschaden?", "How much additional damage?", "Combien de dégâts supplémentaires ?",
                 "Anzahl und Seitenzahl der Würfel sind erforderlich.", "Both dice count and sides are required.",
                 "Le nombre de dés et de faces est requis."), kind="structured", answer_type="g1.answer.dice",
            dependencies=("flame.behavior", "flame.timing"), conditions=DAMAGE, priority=85),
        Question("flame.damage_type", ("flames", "damageType"), {"enum": ["fire"]},
            text("Welche Schadensart?", "Which damage type?", "Quel type de dégâts ?",
                 "Dieser G1-Ausschnitt unterstützt Feuerschaden ohne automatische Resistenzen.",
                 "This G1 slice supports fire damage without automatic resistances.",
                 "Cette tranche G1 prend en charge le feu sans résistances automatiques."),
            dependencies=("flame.behavior",), conditions=DAMAGE, priority=35),
        Question("flame.targets", ("flames", "targets"), {"enum": ["committed_hit_target"]},
            text("Welches Ziel wird betroffen?", "Which target is affected?", "Quelle cible est affectée ?",
                 "Nur das Ziel des bestätigten Treffers; keine neue Zielauswahl.",
                 "Only the committed hit's target; no new target is selected.",
                 "Uniquement la cible de la touche confirmée ; aucune nouvelle cible."),
            dependencies=("flame.behavior", "flame.timing"), conditions=DAMAGE, priority=30),
    ), compiler_version=COMPILER_VERSION)


def content_schema():
    guide = interview()
    properties = {"name": guide.by_id["item.name"].schema, "prose": guide.by_id["item.prose"].schema,
                  "flames": object_schema({q.path[-1]: q.schema for q in guide.questions if q.path[0] == "flames"}, required=[])}
    return object_schema(properties, required=["name"])


def quality_gates(state, declared_quality):
    guide = interview()
    content = guide.values(state)
    gates = []
    if not content.get("name"):
        gates.append({"path": ["name"], "code": "ANSWER_REQUIRED", "questionId": "item.name"})
    if declared_quality == "lore_only":
        return gates
    if declared_quality not in {"sheet_ready", "runtime_ready", "automation_complete"}:
        refuse("SCHEMA_INVALID")
    flame = content.get("flames", {})
    if not flame.get("behavior"):
        gates.append({"path": ["flames", "behavior"], "code": "ANSWER_REQUIRED", "questionId": "flame.behavior"})
    if declared_quality == "sheet_ready":
        return gates
    for q in guide.questions:
        if q.required and guide.visible(q, state) and q.id not in state["answers"]:
            gate = {"path": list(q.path), "code": "ANSWER_REQUIRED", "questionId": q.id}
            if gate not in gates:
                gates.append(gate)
    behavior = flame.get("behavior")
    if behavior not in ("visual", "damage"):
        gates.append({"path": ["flames", "behavior"], "code": "MANUAL_BEHAVIOR"})
    timing = "activation" if behavior == "visual" else "after_hit"
    if "timing" in flame and flame["timing"] != timing:
        gates.append({"path": ["flames", "timing"], "code": "UNSUPPORTED_TIMING"})
    window = "g1.flame.activation" if behavior == "visual" else "g1.flame.hit"
    if "duration" in flame and flame["duration"] != {"kind": "window", "windowId": window}:
        gates.append({"path": ["flames", "duration"], "code": "MANUAL_DURATION"})
    for field in ("initialCharges", "cost"):
        if field in flame and "maximumCharges" in flame and flame[field] > flame["maximumCharges"]:
            gates.append({"path": ["flames", field], "code": "RESOURCE_BOUND_EXCEEDED"})
    # Recovery is an explicitly attested event, and hits require adjudication.
    if declared_quality == "automation_complete":
        gates.append({"path": ["flames", "recovery"], "code": "HUMAN_EVENT_ATTESTATION_REQUIRED"})
    return gates


def preset(preset_id, *, locale="de"):
    if preset_id not in ("g1.harmless-flames", "g1.post-hit-flames") or locale not in ("de", "en", "fr"):
        refuse("NOT_FOUND")
    damage = preset_id == "g1.post-hit-flames"
    values = {"item.name": "Flame sword", "flame.behavior": "damage" if damage else "visual",
        "flame.timing": "after_hit" if damage else "activation",
        "flame.duration": {"kind": "window", "windowId": "g1.flame.hit" if damage else "g1.flame.activation"},
        "flame.maximum": 3, "flame.initial": 3, "flame.cost": 1, "flame.recovery": "long_rest"}
    if damage:
        values.update({"flame.damage": {"count": 2, "sides": 6}, "flame.damage_type": "fire", "flame.targets": "committed_hit_target"})
    guide = interview()
    decisions = [{"question": {"questionId": q.id, "questionVersion": q.version}, "answer": q.answer(values[q.id])}
                 for q in guide.questions if q.id in values]
    document = {"presetId": preset_id, "version": 1, "compilerVersion": COMPILER_VERSION, "decisions": decisions,
                "locale": locale, "labels": {q.id: q.text[locale] for q in guide.questions if q.id in values}}
    return {**document, "previewDigest": content_digest(document)}


def apply_preset(state, reference, digest, *, author, locale):
    previews = [preset(reference["presetId"], locale=language) for language in ("de", "en", "fr")]
    document = next((preview for preview in previews if preview["previewDigest"] == digest), None)
    if reference["version"] != 1 or document is None:
        refuse("PRESET_PREVIEW_STALE")
    # A1 has no locale field on ApplyDraftPreset. The sealed preview identifies
    # the language actually reviewed, independently of the draft's first locale.
    locale = document["locale"]
    guide = interview()
    pending = list(document["decisions"])
    result, logs = copy(state), []
    while pending:
        decision = next((d for d in pending if guide.ready(guide.question(d["question"]), result)), None)
        if decision is None:
            refuse("GUIDE_DEAD_END")
        result, mutations, invalidated = guide.change(result, decision["question"], answer=decision["answer"],
            author=author, locale=locale, source="preset:" + reference["presetId"])
        logs.append({**decision, "promptLocale": locale, "mutations": mutations, "invalidated": invalidated})
        pending.remove(decision)
    return result, logs
