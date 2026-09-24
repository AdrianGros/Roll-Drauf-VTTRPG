"""core-safe-1 evaluator (G1 work package WP2; spec v1.1.4 §6–7, §18).

Interface: ``evaluate`` plus its input and result types, the node parsers,
``EffectApplication.from_wire`` and ``Fuel``. Everything else is internal.
Evaluation is always a full recomputation; incremental evaluation and T16
belong to G2 (decision D5).
"""

from vtt.creation_engine.evaluator.effects import EffectApplication, NumericChange, Operator, StackPolicy
from vtt.creation_engine.evaluator.engine import (Binding, BindingResult, Contribution, Evaluation, Inputs, Limits,
                                                  Rounding, evaluate)
from vtt.creation_engine.evaluator.fuel import CHECKPOINT_OPERATIONS, ROOT_ACTION_OPERATIONS, Fuel
from vtt.creation_engine.evaluator.functions import CORE_ARITIES, CORE_FUNCTIONS
from vtt.creation_engine.evaluator.nodes import (MAX_DEPTH, MAX_NODES, STAGES, Formula, Predicate, Stage,
                                                 parse_formula, parse_predicate)

__all__ = [
    "Binding", "BindingResult", "CHECKPOINT_OPERATIONS", "CORE_ARITIES", "CORE_FUNCTIONS", "Contribution",
    "EffectApplication", "Evaluation", "Formula", "Fuel", "Inputs", "Limits", "MAX_DEPTH", "MAX_NODES",
    "NumericChange", "Operator", "Predicate", "ROOT_ACTION_OPERATIONS", "Rounding", "STAGES", "StackPolicy",
    "Stage", "evaluate", "parse_formula", "parse_predicate",
]
