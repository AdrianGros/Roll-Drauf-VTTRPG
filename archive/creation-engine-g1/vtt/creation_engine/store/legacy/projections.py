"""Labelled RDL builders. Imported metadata never enters the evaluator."""

from sqlalchemy import select

from vtt.creation_engine.adapter.mapping import BINDINGS
from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.evaluator.engine import Binding, evaluate
from vtt.creation_engine.evaluator.effects import EffectApplication
from vtt.creation_engine.policy import Document, Field, Source
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.migration_models import CeLegacyInput
from vtt.creation_engine.store.runtime_models import CeCheckpoint, CeEffectApplication, CeInstance, CeResourceLedger
from vtt.creation_engine.types import InstanceRef
from vtt.creation_engine.units import Quantity


class RdlDocuments:
    def __init__(self, ruleset):
        self.ruleset = ruleset

    def document(self, tx, object_id):
        instance = tx.session.get(CeInstance, object_id)
        if instance is None or instance.scope_id != tx.scope.id:
            return None
        revision = tx.content.revision(instance.revision_id)
        inputs = tx.session.get(CeLegacyInput, instance.id)
        if inputs is None:
            return None
        content, policy, private = revision.content, instance.id, instance.id + ":private"
        fields = {"name": Field(content["name"], policy), "legacyMetadata": Field(content["legacyMetadata"], private)}
        if inputs.equipped is not None:
            fields["is_equipped"] = Field(inputs.equipped, policy)
        bases, overrides = parse_strict_json(inputs.bases), parse_strict_json(inputs.overrides)
        if bases:
            effects = [EffectApplication.from_wire(parse_strict_json(row.canonical)) for row in tx.session.scalars(
                select(CeEffectApplication).where(CeEffectApplication.target_id == instance.id))]
            result = evaluate(InstanceRef(instance.id, tx.scope.id), [Binding(key, self.ruleset.binding(key).unit,
                Quantity.from_wire(overrides.get(key, value)), self.ruleset.binding(key).final_rounding)
                for key, value in bases.items()], effects, units=self.ruleset.units)
            # Include all effect labels conservatively, including conditional facts.
            sources = (Source(policy, "legacy_baseline"),) + tuple(Source(e.policy_id, "effect") for e in effects)
            for column, binding in BINDINGS.items():
                value = result.results[binding]
                fields[column.removesuffix("_score")] = Field(value.value.value.floor() if value.value else None, policy, sources=sources)
            for resource_id, column in (("hp", "hp_current"), ("fokus", "mana_current")):
                row = tx.session.get(CeResourceLedger, (instance.id, resource_id))
                fields[column] = Field(Rational.from_wire(parse_strict_json(row.current)).floor(), policy)
            fields["provenance"] = Field({"bases": "imported_legacy_baseline", "overriddenBindings": sorted(overrides)}, policy)
            fields["character_data"] = Field(content["legacyMetadata"]["character"]["character_data"], private)
        children = tuple(self.document(tx, key) for key in tx.session.scalars(select(CeInstance.id).where(
            CeInstance.holder_id == instance.id).order_by(CeInstance.id)))
        return Document(instance.id, policy, fields, children=children, manual=bool(content.get("manual")))

    def snapshot(self, tx):
        return [self.document(tx, key) for key in tx.session.scalars(select(CeInstance.id).where(
            CeInstance.scope_id == tx.scope.id).order_by(CeInstance.id))]

    def event(self, tx, raw):
        action = tx.action(raw["actionId"])
        payload = parse_strict_json(action.request)["payload"]
        ref = payload.get("instance") or payload.get("item") or payload.get("actorInstance")
        if ref is None:
            return None
        return Document("event:" + raw["eventId"].split(":")[-1], ref["id"], {
            "kind": Field(raw["kind"], ref["id"]), "instanceId": Field(ref["id"], ref["id"])
        }, children=(self.document(tx, ref["id"]),))

    def outcome(self, tx, action, internal):
        checkpoint = tx.session.get(CeCheckpoint, action.last_checkpoint_id)
        if checkpoint is None:
            return None
        payload = parse_strict_json(action.request)["payload"]
        ref = payload.get("instance") or payload.get("item") or payload.get("actorInstance")
        if ref is None:
            return None
        value = parse_strict_json(checkpoint.outcome)
        return Document(checkpoint.id, ref["id"], {"outcome": Field(value, ref["id"] + ":private")},
                        manual=value.get("manual") is True)
