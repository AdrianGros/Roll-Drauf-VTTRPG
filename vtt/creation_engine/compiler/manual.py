"""Private manual instruction cards and lore; never an executable prose adapter."""

from vtt.creation_engine.content import SchemaTypeRef
from vtt.creation_engine.kernel.records import refuse
from .flame import integer, object_schema, text
from .interview import Interview, Question

CONDITIONAL = SchemaTypeRef("g1.authored-manual-conditional", 1)
CHOICE = SchemaTypeRef("g1.authored-manual-choice", 1)
LORE = SchemaTypeRef("g1.authored-lore", 1)
TYPES = (CONDITIONAL, CHOICE, LORE)
TEXT = {"type": "string", "minLength": 1, "maxLength": 2048, "pattern": r"\S"}


def interview(schema_type):
    if schema_type not in TYPES:
        refuse("AUTHORING_REGISTRY_MISMATCH")
    questions = [
        Question("content.name", ("name",), {**TEXT, "maxLength": 200},
            text("Titel", "Title", "Titre", "Der Titel legt keine Regeln fest.",
                 "The title does not establish mechanics.", "Le titre ne définit aucune mécanique."), priority=100),
        Question("content.prose", ("prose",), {**TEXT, "maxLength": 8192},
            text("Beschreibung", "Description", "Description", "Dein Text bleibt Beschreibung. Es werden keine Regeln daraus abgeleitet.",
                 "Your text stays descriptive. No rules are inferred from it.",
                 "Votre texte reste descriptif. Aucune règle n'en est déduite."), required=schema_type == LORE),
    ]
    if schema_type == CONDITIONAL:
        fields = (
            ("affected", "Welcher Wert wird verändert?", "Which value changes?", "Quelle valeur change ?",
             "Nenne Wert und betroffenes Wesen oder Objekt ausdrücklich.", "Name the value and the affected actor or object explicitly.", "Nommez explicitement la valeur et l'acteur ou l'objet concerné."),
            ("when", "Unter welcher Bedingung?", "Under which condition?", "Sous quelle condition ?",
             "Beschreibe, wann die Wirkung gilt. Ein Mensch prüft diese Bedingung.", "Describe when the effect applies. A person checks this condition.", "Décrivez quand l'effet s'applique. Une personne vérifie cette condition."),
            ("change", "Wie verändert sich der Wert?", "How does the value change?", "Comment la valeur change-t-elle ?",
             "Gib Änderung und Einheit an. Die Änderung wird manuell angewendet.", "Specify the change and unit. The change is applied manually.", "Précisez la modification et l'unité. La modification est appliquée manuellement."),
            ("until", "Wann endet die Wirkung?", "When does the effect end?", "Quand l'effet se termine-t-il ?",
             "Beschreibe Ende und Rücknahme ausdrücklich; auch eine dauerhafte Änderung muss gewählt werden.", "Describe the end and removal explicitly; a permanent change must also be chosen.", "Décrivez explicitement la fin et le retrait ; un changement permanent doit aussi être choisi."),
        )
        for index, (key, *labels) in enumerate(fields):
            questions.append(Question("condition." + key, ("condition", key), TEXT,
                text(*labels), priority=90 - index,
                dependencies=("condition." + fields[index - 1][0],) if index else ()))
    elif schema_type == CHOICE:
        questions.extend([
            Question("choice.prompt", ("choice", "prompt"), TEXT,
                text("Wer wählt was und wann?", "Who chooses what, and when?", "Qui choisit quoi et quand ?",
                     "Beschreibe Anlass und Teilnahmebedingungen. Sie werden manuell geprüft.",
                     "Describe the trigger and eligibility. They are checked manually.",
                     "Décrivez le déclencheur et les conditions de participation. Ils sont vérifiés manuellement."), priority=90),
            Question("choice.count", ("choice", "count"), integer(2, 6),
                text("Wie viele Alternativen gibt es?", "How many alternatives are there?", "Combien d'alternatives y a-t-il ?",
                     "Zwei bis sechs. Eine Änderung macht die bisherigen Alternativen und die Auswahlzahl ungültig.",
                     "Two to six. Changing this invalidates previous alternatives and the selection count.",
                     "Deux à six. Un changement invalide les anciennes alternatives et le nombre de sélections."),
                kind="structured", answer_type="g1.manual.answer.alternative-count", dependencies=("choice.prompt",), priority=80),
            Question("choice.selection", ("choice", "selection"), integer(1, 6),
                text("Wie viele Alternativen sollen gewählt werden?", "How many alternatives must be selected?", "Combien d'alternatives faut-il sélectionner ?",
                     "Wähle eine genaue Anzahl. Auswahl und Konsequenzen werden manuell aufgelöst.",
                     "Choose an exact count. Selection and consequences are resolved manually.",
                     "Choisissez un nombre exact. La sélection et les conséquences sont résolues manuellement."),
                kind="structured", answer_type="g1.manual.answer.selection-count", dependencies=("choice.count",), priority=10),
        ])
        for index in range(1, 7):
            key = f"choice.option{index}"
            conditions = (("choice.count", tuple(range(max(2, index), 7))),)
            questions.extend([
                Question(key + ".label", ("choice", "alternatives", str(index), "label"), {**TEXT, "maxLength": 200},
                    text(f"Alternative {index}", f"Alternative {index}", f"Alternative {index}",
                         "Gib dieser Alternative einen eindeutigen Namen.", "Give this alternative a distinct name.", "Donnez à cette alternative un nom distinct."),
                    dependencies=("choice.count",), conditions=conditions, priority=70 - index * 2),
                Question(key + ".consequence", ("choice", "alternatives", str(index), "consequence"), TEXT,
                    text(f"Konsequenz von Alternative {index}", f"Consequence of alternative {index}", f"Conséquence de l'alternative {index}",
                         "Beschreibe die Konsequenz ausdrücklich, auch wenn keine vorgesehen ist. Es wird nichts automatisch angewendet.",
                         "Describe the consequence explicitly, including when there is none. Nothing is applied automatically.",
                         "Décrivez explicitement la conséquence, y compris s'il n'y en a aucune. Rien n'est appliqué automatiquement."),
                    dependencies=("choice.count", key + ".label"), conditions=conditions, priority=69 - index * 2),
            ])
    return Interview(questions, compiler_version=schema_type.type_id + ":1")


def content_schema(schema_type):
    properties = {}
    for q in interview(schema_type).questions:
        parent = properties
        for key in q.path[:-1]:
            parent = parent.setdefault(key, object_schema({}, required=[]))["properties"]
        parent[q.path[-1]] = q.schema
    return object_schema(properties, required=["name"])


def quality_gates(schema_type, state, quality):
    guide = interview(schema_type)
    content = guide.values(state)
    gates = []
    required = [q for q in guide.questions if q.required and guide.visible(q, state)]
    if quality == "lore_only" and schema_type != LORE:
        required = [guide.by_id["content.name"]]
    for q in required:
        if q.id not in state["answers"]:
            gates.append({"path": list(q.path), "code": "ANSWER_REQUIRED", "questionId": q.id})
    if quality != "lore_only":
        if schema_type == LORE:
            gates.append({"path": [], "code": "DESCRIPTIVE_ONLY"})
        if schema_type == CHOICE:
            choice = content.get("choice", {})
            if choice.get("selection", 0) > choice.get("count", 0):
                gates.append({"path": ["choice", "selection"], "code": "CHOICE_COUNT_EXCEEDED"})
            labels = set()
            for key, option in choice.get("alternatives", {}).items():
                label = option.get("label", "").strip().casefold()
                if label and label in labels:
                    gates.append({"path": ["choice", "alternatives", key, "label"], "code": "CHOICE_LABEL_DUPLICATE"})
                labels.add(label)
        if quality in {"runtime_ready", "automation_complete"}:
            gates.append({"path": [], "code": "MANUAL_PROFILE_ONLY"})
    return gates
