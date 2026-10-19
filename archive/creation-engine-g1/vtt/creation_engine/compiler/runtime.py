"""G1 native flame registrations. Existing RDL 1.0.0 artifacts stay immutable."""

from dataclasses import replace

from vtt.creation_engine.adapter import mapping
from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.content import SchemaRegistry, SchemaType, SchemaTypeRef
from vtt.creation_engine.content.rdl_g1 import rdl_g1_ruleset
from vtt.creation_engine.content.ruleset import BindingTemplate, ResourceSpec, AdjustBoundPolicy
from vtt.creation_engine.evaluator.engine import Rounding
from vtt.creation_engine.kernel.activity import Activity, Cost, Dice, Window
from vtt.creation_engine.kernel.decisions import Question
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.units import Unit, UnitTable, Quantity
from . import catalog, flame

CONFIGURATION = {**mapping.CONFIGURATION, "authoredRuntime": "g1.flames:1", "rollAdjustments": "declared-sum:1"}
ANSWER_TYPE = SchemaTypeRef("g1.runtime.boolean", 1)
DECISION_POLICY = "g1.flame.decision"
FLAME_QUESTION = "g1.flame.use"
ACTIVATE = "g1.flame.activate"
HIT = "g1.flame.confirmed-hit"
DAMAGE = "g1.flame.damage-child"
RECOVER = "g1.flame.recover."


def ruleset():
    base = rdl_g1_ruleset()
    units = [Unit(u["id"], u["dimension"], Rational.from_wire(u["toBase"])) for u in base.units.canonical_form()["units"]]
    units.append(Unit("g1:charge", "g1:charge-count", Rational.of(1)))
    return replace(base, version="1.1.0", units=UnitTable(units),
        bindings=(*base.bindings, BindingTemplate("charges_max", "g1:charge", Rounding.FLOOR)),
        resources=(*base.resources, ResourceSpec("charges", "g1:charge", "charges_max", AdjustBoundPolicy.CLAMP_REPORT_DELTA)))


def registry():
    legacy, authored = mapping.registry(), catalog.registry()
    types = [legacy.get(t) for t in (mapping.CHARACTER_TYPE, mapping.ITEM_TYPE)]
    types.append(authored.get(flame.ITEM_TYPE))
    types.append(SchemaType(ANSWER_TYPE.type_id, 1, flame.object_schema({"kind": {"const": "boolean"}, "value": {"type": "boolean"}})))
    return SchemaRegistry("g1.native-runtime-schemas", "1", types)


def runtime_content(revision):
    if revision.schema_type != flame.ITEM_TYPE:
        refuse("SEMANTIC_INVALID", "only explicitly authored flame activities are registered")
    provenance = parse_strict_json(revision.provenance)
    if provenance.get("registry") != catalog.registry().artifact() or provenance.get("compilerVersion") != flame.COMPILER_VERSION:
        refuse("AUTHORING_REGISTRY_MISMATCH", "the authored revision requires its original compiler registration")
    if provenance.get("declaredQuality") not in {"runtime_ready", "automation_complete"}:
        refuse("QUALITY_CLAIM_UNMET")
    guide, content = flame.interview(), revision.content
    state = guide.empty()
    for q in guide.questions:
        value = content
        for key in q.path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            state, _, _ = guide.change(state, {"questionId": q.id, "questionVersion": q.version},
                                      answer=q.answer(value), author=revision.author_user_id, locale="de")
    questions = [{"questionId": key, "questionVersion": answer["questionVersion"]}
                 for key, answer in sorted(state["answers"].items())]
    if provenance.get("questions") != questions:
        refuse("AUTHORING_REGISTRY_MISMATCH", "revision question provenance does not match its compiler")
    if flame.quality_gates(state, "runtime_ready"):
        refuse("QUALITY_CLAIM_UNMET")
    return content["flames"]


def resolve_activity(revision, activity_id):
    f = runtime_content(revision)
    cost = Cost("source", "charges", Quantity(Rational.of(f["cost"]), "g1:charge"))
    if activity_id == ACTIVATE and f["behavior"] == "visual":
        return Activity(activity_id, (Window("g1.flame.activation", (cost,), (), 8),))
    if activity_id == HIT and f["behavior"] == "damage":
        question = Question(FLAME_QUESTION, 1, ANSWER_TYPE, "g1.actor-controller", DECISION_POLICY,
                            decline={"kind": "boolean", "value": False})
        return Activity(activity_id, (Window("hit", (), (), 8, True, question), Window("finish", (), (), 8)), (DAMAGE,))
    if activity_id == DAMAGE and f["behavior"] == "damage":
        dice = Dice("fire", f["damage"]["count"], f["damage"]["sides"])
        return Activity(activity_id, (Window("g1.flame.hit", (cost,), (dice,), dice.count + 8),))
    if activity_id == RECOVER + f["recovery"]:
        return Activity(activity_id, (Window("recovery", (), (), 8),))
    refuse("SEMANTIC_INVALID", "activity is not registered for this authored behavior")
