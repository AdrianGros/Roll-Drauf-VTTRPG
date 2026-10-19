"""Pure RDL G1 mapping: preserve observed totals without inventing history.

The supplied snapshot is detached JSON. Only these named columns become
mechanical inputs. All original JSON and unsupported capabilities remain in
legacyMetadata, which is never passed to the evaluator.
"""

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import SchemaRegistry, SchemaType, SchemaTypeRef
from vtt.creation_engine.content.rdl_g1 import ATTRIBUTES, rdl_g1_ruleset
from vtt.creation_engine.evaluator.engine import Binding, evaluate
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import InstanceRef
from vtt.creation_engine.units import Quantity

VERSION = 1
CHARACTER_TYPE = SchemaTypeRef("rdl.g1.legacy-character", 1)
ITEM_TYPE = SchemaTypeRef("rdl.g1.legacy-item", 1)
BINDINGS = {**{f"{key}_score": key for key in ATTRIBUTES}, "ac": "defense",
            "proficiency_bonus": "training_bonus", "hp_max": "hp_max", "mana_max": "fokus_max"}
RESOURCES = {"hp_current": "hp", "mana_current": "fokus"}
CONFIGURATION = {"adapter": "rdl-g1-legacy:1", "nativeCommands": "rdl-g1-inputs:1", "declassifications": []}


def registry():
    quantity = {"$ref": "urn:rolldrauf:creation-engine:contracts:1.1.3#/$defs/Quantity"}
    actor = {"type": "object", "properties": {
        "name": {"type": "string"}, "bases": {"type": "object", "properties": {
            key: quantity for key in BINDINGS.values()}, "required": list(BINDINGS.values()), "additionalProperties": False},
        "legacyMetadata": {}, "selections": {"type": "object", "properties": {
            choice.id: {"enum": list(choice.options)} for choice in rdl_g1_ruleset().choices}, "additionalProperties": False},
        "provenance": {"const": "imported_legacy_baseline"}},
        "required": ["name", "bases", "selections", "legacyMetadata", "provenance"], "additionalProperties": False}
    item = {"type": "object", "properties": {"name": {"type": "string"}, "legacyMetadata": {},
        "manual": {"const": True}}, "required": ["name", "legacyMetadata", "manual"], "additionalProperties": False}
    return SchemaRegistry("rdl.g1.legacy-schemas", "1", [
        SchemaType(CHARACTER_TYPE.type_id, 1, actor), SchemaType(ITEM_TYPE.type_id, 1, item)])


def map_character(snapshot, instance_id, scope_id):
    source = parse_strict_json(canonical_bytes(snapshot))
    character = source["character"]
    rules = rdl_g1_ruleset()
    bases = {}
    for column, binding_id in BINDINGS.items():
        value = character[column]
        if type(value) is not int or not -(2**53 - 1) <= value <= 2**53 - 1:
            refuse("SEMANTIC_INVALID", "legacy numeric input is missing or unsupported")
        bases[binding_id] = Quantity(Rational.of(value), rules.binding(binding_id).unit).to_wire()
    evaluation = evaluate(InstanceRef(instance_id, scope_id), [
        Binding(key, rules.binding(key).unit, Quantity.from_wire(value), rules.binding(key).final_rounding)
        for key, value in bases.items()], (), units=rules.units)
    fields = [{"sourceField": column, "bindingId": key, "legacyValue": character[column],
               "engineValue": evaluation.results[key].value.value.floor(),
               "provenance": "imported_legacy_baseline"} for column, key in BINDINGS.items()]
    resources, differences = {}, []
    for column, resource_id in RESOURCES.items():
        spec = next(resource for resource in rules.resources if resource.id == resource_id)
        current = character[column]
        maximum = evaluation.results[spec.maximum_binding].value.value.floor()
        if type(current) is not int or maximum < 0:
            refuse("SEMANTIC_INVALID", "legacy resource has no valid current/maximum")
        proposed = max(0, min(maximum, current))
        resources[resource_id] = {"current": proposed, "maximum": maximum, "unit": spec.unit}
        fields.append({"sourceField": column, "resourceId": resource_id, "legacyValue": current,
                       "engineValue": proposed, "provenance": "imported_legacy_current"})
        if current != proposed:
            differences.append({"field": column, "legacyValue": current, "engineValue": proposed,
                                "keepLegacyAllowed": False, "reason": "resource_bounds"})
    for token in source["tokens"]:
        for column, value in (("hp_current", resources["hp"]["current"]), ("hp_max", resources["hp"]["maximum"])):
            if token[column] is not None and token[column] != value:
                differences.append({"field": f"token:{token['id']}:{column}", "legacyValue": token[column],
                    "engineValue": value, "keepLegacyAllowed": False, "reason": "representation_disagrees_with_sheet"})
    # Textual signatures/equipment bonuses never get added to a total of unknown origin.
    unsupported = ["Historical contributions are unknown; totals remain labelled legacy baselines.",
                   "Progression, spells and imported item mechanics remain manual/inert."]
    data = character.get("character_data")
    data = data if isinstance(data, dict) else {}
    rdl = data.get("roll_drauf_light", {})
    content = rdl.get("content", {}) if isinstance(rdl, dict) else {}
    features = content.get("class_features", []) if isinstance(content, dict) else []
    features = features if isinstance(features, list) else []
    selected = {f.get("slug") for f in features if isinstance(f, dict) and isinstance(f.get("slug"), str)}
    selections = {}
    for choice in rules.choices:
        recognized = selected & set(choice.options)
        if len(recognized) == 1:
            selections[choice.id] = recognized.pop()
        elif recognized:
            unsupported.append("Conflicting imported selection remains manual: " + choice.id)
    return {"content": {"name": character["name"], "bases": bases, "legacyMetadata": source,
                        "selections": selections, "provenance": "imported_legacy_baseline"},
            "fields": fields, "resources": resources, "differences": differences, "unsupported": unsupported}
