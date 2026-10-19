"""Current-policy projections for authored items and native checkpoint outcomes."""

from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.compiler import flame
from vtt.creation_engine.compiler import runtime as registered
from vtt.creation_engine.policy import Document, Field, Source
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.legacy.projections import RdlDocuments
from vtt.creation_engine.store.migration_models import CeLegacyInput
from vtt.creation_engine.store.runtime_models import CeCheckpoint, CeInstance, CeResourceLedger


class NativeDocuments(RdlDocuments):
    def document(self, tx, object_id):
        instance = tx.session.get(CeInstance, object_id)
        if instance is None or instance.scope_id != tx.scope.id:
            return None
        revision = tx.content.revision(instance.revision_id)
        if revision.schema_type != flame.ITEM_TYPE:
            return super().document(tx, object_id)
        row = tx.session.get(CeResourceLedger, (instance.id, "charges"))
        inputs = tx.session.get(CeLegacyInput, instance.id)
        f = registered.runtime_content(revision)
        policy, private = instance.id, instance.id + ":private"
        return Document(instance.id, policy, {
            "name": Field(revision.content["name"], policy), "description": Field(revision.content.get("prose", ""), policy),
            "revision": Field(revision.ref().to_wire(), private), "holderId": Field(instance.holder_id, private),
            "behavior": Field(f["behavior"], private), "recovery": Field(f["recovery"], private),
            "charges": Field(Rational.from_wire(parse_strict_json(row.current)).floor(), policy),
            "maximumCharges": Field(Rational.from_wire(parse_strict_json(row.maximum)).floor(), policy),
            "is_equipped": Field(inputs.equipped, policy),
        })

    @staticmethod
    def _reference(tx, action, checkpoint):
        payload = parse_strict_json(action.request)["payload"]
        ref = payload.get("instance") or payload.get("item") or payload.get("actorInstance")
        if ref is None and checkpoint is not None:
            instance_id = parse_strict_json(checkpoint.outcome).get("instanceId")
            if instance_id:
                ref = {"id": instance_id}
        return ref

    def event(self, tx, raw):
        action = tx.action(raw["actionId"])
        checkpoint = tx.session.get(CeCheckpoint, raw["checkpointId"]) if raw.get("checkpointId") else None
        ref = self._reference(tx, action, checkpoint)
        if ref is None:
            return None
        payload = parse_strict_json(action.request)["payload"]
        required = tuple(r["id"] for r in [payload.get("actorInstance"), payload.get("sourceInstance"), *payload.get("targets", [])] if r)
        return Document("event:" + raw["eventId"].split(":")[-1], ref["id"], {
            "kind": Field(raw["kind"], ref["id"]), "instanceId": Field(ref["id"], ref["id"])
        }, children=(self.document(tx, ref["id"]),), required_policies=required)

    def outcome(self, tx, action, internal):
        checkpoint = tx.session.get(CeCheckpoint, action.last_checkpoint_id)
        ref = self._reference(tx, action, checkpoint)
        if checkpoint is None or ref is None:
            return None
        payload = parse_strict_json(action.request)["payload"]
        involved = [payload.get("actorInstance"), payload.get("sourceInstance"), *payload.get("targets", [])]
        labels = tuple(Source(r["id"] + ":private", "native_checkpoint") for r in involved if r)
        value = parse_strict_json(checkpoint.outcome)
        return Document(checkpoint.id, ref["id"], {"outcome": Field(value, ref["id"] + ":private", sources=labels)},
                        manual=value.get("manual") is True or value.get("result", {}).get("manual") is True)
