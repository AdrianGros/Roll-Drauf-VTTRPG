"""Registered RDL input commands, using the existing checkpoint/receipt protocol."""

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.activity import Activity, Window
from vtt.creation_engine.kernel.records import Action, ActionState, receipt, refuse
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.migration_models import CeLegacyInput
from vtt.creation_engine.store.runtime_models import CeResourceLedger
from vtt.creation_engine.units import Quantity

OPERATIONS = frozenset(("SetBaseValue", "SetValueOverride", "ClearValueOverride", "SetItemEquipped"))


def submit(kernel, principal, command, *, record_request=None):
    wire, payload = command.wire, command.wire["payload"]
    with kernel.store.transaction(wire["scopeId"]) as tx:
        kernel._authorize(tx, principal, command)
        if wire["authorityEpoch"] != tx.scope.authority_epoch:
            refuse("AUTHORITY_EPOCH_MISMATCH")
        existing = tx.receipt(principal, wire["idempotencyKey"])
        if existing:
            if existing["requestDigest"] != command.digest:
                refuse("IDEMPOTENCY_KEY_REUSE")
            return existing
        kernel._authority(tx, command, check_version=True)
        if tx.scope.active_action_id:
            refuse("SCOPE_BUSY")
        instance = tx.instance(payload.get("instance", payload.get("item")))
        row = tx.session.get(CeLegacyInput, instance.id)
        if row is None:
            refuse("NOT_FOUND")
        op = wire["operation"]
        if op == "SetItemEquipped":
            if row.equipped is None or instance.holder_id is None:
                refuse("SEMANTIC_INVALID", "occurrence is not equippable")
            before, after = row.equipped, payload["equipped"]
            row.equipped = after
            field = "equipped"
        else:
            field = payload["bindingId"]
            binding = kernel.ruleset.binding(field)
            if not (binding.base_editable if op == "SetBaseValue" else binding.overrideable):
                refuse("BINDING_NOT_OVERRIDEABLE")
            bases, overrides = parse_strict_json(row.bases), parse_strict_json(row.overrides)
            if field not in bases:
                refuse("NOT_FOUND")
            values = bases if op == "SetBaseValue" else overrides
            before = values.get(field)
            if op == "ClearValueOverride":
                values.pop(field, None)
                after = None
            else:
                quantity = kernel.ruleset.units.convert(Quantity.from_wire(payload["value"]), binding.unit)
                if quantity.value.denominator != 1:
                    refuse("SEMANTIC_INVALID", "RDL base inputs use integer points")
                after = quantity.to_wire()
                values[field] = after
            row.bases, row.overrides = canonical_bytes(bases), canonical_bytes(overrides)
            for resource in kernel.ruleset.resources:
                if resource.maximum_binding == field:
                    maximum = Quantity.from_wire(overrides.get(field, bases[field])).value
                    ledger = tx.session.get(CeResourceLedger, (instance.id, resource.id))
                    current = Rational.from_wire(parse_strict_json(ledger.current))
                    if maximum < current or maximum < Rational.of(0):
                        refuse("RESOURCE_BOUND_EXCEEDED", "a maximum edit cannot silently discard a resource")
                    ledger.maximum = canonical_bytes(maximum.to_wire())
        action_id, checkpoint_id = new_id("action"), new_id("checkpoint")
        plan = Activity("rdl.input", (Window("input", (), (), 1),))
        action = Action(action_id, tx.scope.id, principal, command.canonical, plan.canonical(),
                        ActionState.COMPLETED, tx.now, action_id, next_window=1, last_checkpoint_id=checkpoint_id)
        tx.claim_lease(kernel.worker_id)
        tx.release_lease = True
        tx.save_action(action)
        tx.scope.state_version += 1
        outcome = {"manual": True, "adjudicator": principal, "reason": payload.get("reason", "item equip state"),
                   "instanceId": instance.id, "field": field, "before": before, "after": after, "changes": []}
        tx.save_checkpoint(action, checkpoint_id, outcome, (), (), (), index=0)
        event_id = tx.event(action, "input_changed", checkpoint_id)
        result = receipt(command, action_id, tx.scope, status="committed", checkpoint_id=checkpoint_id,
                         outcome=outcome, events=[event_id])
        tx.save_receipt(principal, wire["idempotencyKey"], result)
        if record_request:
            record_request(tx, principal, command)
        kernel.fault("before_commit")
    kernel.fault("after_commit")
    return result
