"""Roll Drauf Light G1 subset 1.0.0 (approved G1 plan, D3).

This is an independent, digest-pinned package, not a live import of the
legacy catalogue. It declares only the adapter's supported fields. Values
and signature selections have no defaults. Imported totals and signature
effects require explicit reconciliation in WP7 (§5); selecting a signature
here does not silently apply its descriptive bonus. Other mechanics remain
inert/manual. No full RDL or D&D rules coverage is implied.

All numeric bindings round down to integer points. HP and Fokus are separate
dimensions and bounded resources; adjustment clamps to their known maximum
and reports the actual delta (G0-09). An unresolved maximum remains unresolved.
Override/base-edit eligibility is declared here; authorization belongs to
the command kernel and policy layer.
"""

from vtt.creation_engine.content.ruleset import (AdjustBoundPolicy, BindingTemplate, ChoiceTemplate,
                                               ResourceSpec, Ruleset)
from vtt.creation_engine.evaluator.engine import Rounding
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.units import DIMENSIONLESS, Unit, UnitTable

RULESET_ID = "rules.roll-drauf-light-g1"
RULESET_VERSION = "1.0.0"
ATTRIBUTES = ("str", "dex", "con", "int", "wis", "cha")


def rdl_g1_ruleset() -> Ruleset:
    """Return an isolated copy of the separately versioned G1 declarations."""
    units = UnitTable([
        Unit("unit:dimensionless", DIMENSIONLESS, Rational.of(1)),
        Unit("rdl:point", "rdl:score", Rational.of(1)),
        Unit("rdl:hp", "rdl:health", Rational.of(1)),
        Unit("rdl:fokus", "rdl:focus", Rational.of(1)),
    ])
    return Ruleset(
        RULESET_ID, RULESET_VERSION, units,
        bindings=tuple(BindingTemplate(key, unit, Rounding.FLOOR, overrideable=True, base_editable=True)
                       for key, unit in (
                           *((attribute, "rdl:point") for attribute in ATTRIBUTES),
                           ("defense", "rdl:point"), ("training_bonus", "rdl:point"),
                           ("hp_max", "rdl:hp"), ("fokus_max", "rdl:fokus"))),
        resources=(
            ResourceSpec("hp", "rdl:hp", "hp_max", AdjustBoundPolicy.CLAMP_REPORT_DELTA),
            ResourceSpec("fokus", "rdl:fokus", "fokus_max", AdjustBoundPolicy.CLAMP_REPORT_DELTA),
        ),
        choices=(
            ChoiceTemplate("kaempfer_signature", ("defensiver_stil", "offensiver_stil")),
            ChoiceTemplate("magier_signature", ("arkane_ruestung", "doppelpuls")),
            ChoiceTemplate("schurke_signature", ("meuchler", "fluchtexperte")),
        ),
    )
