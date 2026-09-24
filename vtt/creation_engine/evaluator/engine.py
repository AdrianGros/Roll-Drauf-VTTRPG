"""The core-safe-1 evaluator (spec v1.1.4 §6–7, §18): full recomputation of one occurrence's numeric bindings.

Stages run in fixed order: base -> SET -> ADD -> MULTIPLY -> clamp -> final
rounding. Stack policies filter each stack group before reduction. Equal-
priority SETs that disagree, empty clamp intervals and stacking violations
are EFFECT_CONFLICT; priority never overrides a stack conflict. Missing data
stays explicitly unresolved and is never read as false or zero. The result
does not depend on the order in which applications are supplied.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from vtt.creation_engine.errors import EFFECT_CONFLICT, SEMANTIC_INVALID, BudgetExceeded, ContractViolation
from vtt.creation_engine.evaluator.effects import STAGE_OF, EffectApplication, NumericChange, Operator, StackPolicy
from vtt.creation_engine.evaluator.functions import CORE_FUNCTIONS
from vtt.creation_engine.evaluator.fuel import Fuel
from vtt.creation_engine.evaluator.nodes import (STAGES, And, Call, Compare, Formula, Human, If, IsKnown, Literal,
                                                 ManualToggle, Not, Or, Predicate, PredicateRef, Read, Stage)
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import InstanceRef
from vtt.creation_engine.units import DIMENSIONLESS, Quantity, UnitTable


class Rounding(StrEnum):
    FLOOR = "floor"
    CEIL = "ceil"
    TRUNCATE = "truncate"
    NEAREST_TIES_EVEN = "nearest_ties_even"


@dataclass(frozen=True, slots=True)
class Binding:
    """A numeric target of the occurrence. ``base`` None means the required base value is unknown."""
    id: str
    unit: str
    base: Quantity | None
    final_rounding: Rounding | None = None      # the target schema's explicit final operator (§7)


@dataclass(frozen=True)
class Inputs:
    """Recorded facts the evaluator may read: decision answers, manual toggles, exclusive-group choices."""
    human_answers: Mapping[tuple[str, int, str], bool] = field(default_factory=dict)
    manual_toggles: Mapping[str, bool] = field(default_factory=dict)
    exclusive_choices: Mapping[str, tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Limits:
    max_applications: int = 2_000          # active effect applications per instance (§18)
    max_derived_nodes: int = 10_000        # derived nodes per instance (§18)


@dataclass(frozen=True, slots=True)
class Contribution:
    stage: Stage
    operator: Operator
    value: Quantity
    application_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BindingResult:
    binding_id: str
    status: str                             # "resolved" | "unresolved" | "conflict"
    value: Quantity | None
    stage_values: tuple[tuple[Stage, Quantity | None], ...]
    contributions: tuple[Contribution, ...]
    reasons: tuple[str, ...]
    conflicting_applications: tuple[str, ...]

    @property
    def code(self) -> str | None:
        return EFFECT_CONFLICT if self.status == "conflict" else None


@dataclass(frozen=True, slots=True)
class Evaluation:
    results: Mapping[str, BindingResult]
    fuel_used: int


def evaluate(target: InstanceRef, bindings: Sequence[Binding], applications: Sequence[EffectApplication], *,
             units: UnitTable, predicates: Mapping[str, Predicate] = MappingProxyType({}),
             inputs: Inputs = Inputs(), fuel: Fuel | None = None, limits: Limits = Limits()) -> Evaluation:
    """Evaluate every binding of ``target`` under the active ``applications``."""
    return _Evaluator(target, bindings, applications, units, predicates, inputs, fuel or Fuel(), limits).run()


@dataclass(frozen=True, slots=True)
class _Known:
    value: Quantity


@dataclass(frozen=True, slots=True)
class _Unknown:
    reasons: frozenset[str]


@dataclass(frozen=True, slots=True)
class _Conflict:
    reasons: frozenset[str]
    application_ids: frozenset[str]


_Outcome = _Known | _Unknown | _Conflict
_Truth = bool | _Unknown | _Conflict


def _blocking(outcomes: Iterable[_Outcome | _Truth]) -> _Unknown | _Conflict | None:
    """The combined non-value outcome: any conflict dominates, then unknowns; None if all are values."""
    outcomes = list(outcomes)
    conflicts = [o for o in outcomes if isinstance(o, _Conflict)]
    if conflicts:
        return _Conflict(frozenset().union(*(c.reasons for c in conflicts)),
                         frozenset().union(*(c.application_ids for c in conflicts)))
    unknowns = [o for o in outcomes if isinstance(o, _Unknown)]
    return _Unknown(frozenset().union(*(u.reasons for u in unknowns))) if unknowns else None


@dataclass(frozen=True, slots=True)
class _Candidate:
    operator: Operator
    priority: int
    outcome: _Outcome        # binding unit; MULTIPLY factors in the dimensionless base unit
    application_ids: tuple[str, ...]


_COMPARE = {"lt": Rational.__lt__, "le": Rational.__le__, "eq": Rational.__eq__,
            "ne": Rational.__ne__, "ge": Rational.__ge__, "gt": Rational.__gt__}


class _Evaluator:
    def __init__(self, target, bindings, applications, units, predicates, inputs, fuel, limits):
        if len(applications) > limits.max_applications:
            raise BudgetExceeded(f"more than {limits.max_applications} active effect applications on one instance")
        self.units, self.predicates, self.inputs, self.fuel, self.limits = units, predicates, inputs, fuel, limits
        self.bindings: dict[str, Binding] = {}
        for binding in bindings:
            if binding.id in self.bindings:
                raise ContractViolation(SEMANTIC_INVALID, f"binding {binding.id} is declared twice")
            units.unit(binding.unit)
            if binding.base is not None:
                units.convert(binding.base, binding.unit)
            self.bindings[binding.id] = binding
        self.candidates: dict[tuple[str, Stage], list[tuple[EffectApplication, NumericChange]]] = defaultdict(list)
        seen: set[str] = set()
        for application in sorted(applications, key=lambda a: a.application_id):
            if application.application_id in seen:
                raise ContractViolation(SEMANTIC_INVALID, f"application {application.application_id} is supplied twice")
            seen.add(application.application_id)
            if application.target != target:
                raise ContractViolation(SEMANTIC_INVALID, f"application {application.application_id} targets another occurrence")
            for change in application.changes:
                self._require_binding(change.target_binding_id)
                self.candidates[(change.target_binding_id, STAGE_OF[change.operator])].append((application, change))
        self._check_dependencies()
        self.memo: dict[tuple[str, Stage], _Outcome] = {}
        self.named: dict[str, _Truth] = {}
        self.contributions: dict[str, list[Contribution]] = defaultdict(list)

    def run(self) -> Evaluation:
        results = {binding_id: self._result(binding_id) for binding_id in sorted(self.bindings)}
        return Evaluation(MappingProxyType(results), self.fuel.used)

    # --- static checks -------------------------------------------------------------------------

    def _require_binding(self, binding_id: str) -> None:
        if binding_id not in self.bindings:
            raise ContractViolation(SEMANTIC_INVALID, f"binding {binding_id} is not declared for this occurrence")

    def _check_dependencies(self) -> None:
        """Reject unknown references and dependency cycles before any value is computed (§6)."""
        edges: dict[tuple, set[tuple]] = defaultdict(set)
        for binding_id in self.bindings:
            for earlier, later in zip(STAGES, STAGES[1:]):
                edges[("binding", binding_id, later)].add(("binding", binding_id, earlier))
        for (binding_id, stage), pairs in self.candidates.items():
            for _, change in pairs:
                self._formula_edges(("binding", binding_id, stage), change.value, edges)
        for name, predicate in self.predicates.items():
            self._predicate_edges(("predicate", name), predicate, edges)
        nodes = set(edges).union(*edges.values())
        if len(nodes) > self.limits.max_derived_nodes:
            raise BudgetExceeded(f"more than {self.limits.max_derived_nodes} derived nodes on one instance")
        cycle = _find_cycle(edges)
        if cycle:
            path = " -> ".join(":".join(str(part) for part in node[1:]) for node in cycle)
            raise ContractViolation(SEMANTIC_INVALID, f"dependency cycle: {path}")

    def _formula_edges(self, source: tuple, formula: Formula, edges) -> None:
        pending = [formula]
        while pending:
            node = pending.pop()
            if isinstance(node, Read):
                self._require_binding(node.binding_id)
                edges[source].add(("binding", node.binding_id, node.stage))
            elif isinstance(node, Call):
                pending.extend(node.args)
            elif isinstance(node, If):
                self._require_predicate(node.condition)
                edges[source].add(("predicate", node.condition))
                pending.extend((node.then, node.otherwise))

    def _predicate_edges(self, source: tuple, predicate: Predicate, edges) -> None:
        pending = [predicate]
        while pending:
            node = pending.pop()
            if isinstance(node, PredicateRef):
                self._require_predicate(node.binding_id)
                edges[source].add(("predicate", node.binding_id))
            elif isinstance(node, (And, Or)):
                pending.extend(node.args)
            elif isinstance(node, Not):
                pending.append(node.arg)
            elif isinstance(node, Compare):
                self._formula_edges(source, node.left, edges)
                self._formula_edges(source, node.right, edges)
            elif isinstance(node, IsKnown):
                self._require_binding(node.binding_id)
                edges[source].add(("binding", node.binding_id, Stage.FINAL))

    def _require_predicate(self, name: str) -> None:
        if name not in self.predicates:
            raise ContractViolation(SEMANTIC_INVALID, f"predicate {name} is not registered")

    # --- stages --------------------------------------------------------------------------------

    def _stage(self, binding_id: str, stage: Stage) -> _Outcome:
        key = (binding_id, stage)
        if key not in self.memo:
            binding = self.bindings[binding_id]
            if stage is Stage.BASE:
                outcome = (_Known(self.units.convert(binding.base, binding.unit)) if binding.base is not None
                           else _Unknown(frozenset({f"base value of {binding_id} is unknown"})))
            else:
                previous = self._stage(binding_id, STAGES[STAGES.index(stage) - 1])
                outcome = self._reduce(binding, stage, previous, self._stacked(binding, stage))
            self.memo[key] = outcome
        return self.memo[key]

    def _reduce(self, binding: Binding, stage: Stage, previous: _Outcome, candidates: list[_Candidate]) -> _Outcome:
        if stage is Stage.SET:
            return self._reduce_set(binding, previous, candidates)
        blocked = _blocking([previous, *(c.outcome for c in candidates)])
        if blocked:
            return blocked
        value = previous.value
        if stage is Stage.ADD:
            for candidate in candidates:
                value = Quantity(value.value + candidate.outcome.value.value, value.unit)
                self._record(binding, stage, candidate)
        elif stage is Stage.MULTIPLY:
            for candidate in candidates:
                value = value.scale(candidate.outcome.value.value)
                self._record(binding, stage, candidate)
        elif stage is Stage.CLAMP:
            return self._clamp(binding, value, candidates)
        elif stage is Stage.FINAL and binding.final_rounding is not None:
            method = "round_nearest_ties_even" if binding.final_rounding is Rounding.NEAREST_TIES_EVEN else binding.final_rounding.value
            value = Quantity(Rational.of(getattr(value.value, method)()), value.unit)
        return _Known(value)

    def _reduce_set(self, binding: Binding, previous: _Outcome, candidates: list[_Candidate]) -> _Outcome:
        if not candidates:
            return previous
        conflict = _blocking(c.outcome for c in candidates if isinstance(c.outcome, _Conflict))
        if conflict:
            return conflict          # priority never overrides a conflict (§7)
        top = max(c.priority for c in candidates)
        winners = [c for c in candidates if c.priority == top]
        blocked = _blocking(c.outcome for c in winners)
        if blocked:
            return blocked
        if len({c.outcome.value for c in winners}) > 1:
            ids = frozenset(i for c in winners for i in c.application_ids)
            return _Conflict(frozenset({f"SET candidates at priority {top} disagree on {binding.id}"}), ids)
        merged = _Candidate(Operator.SET, top, winners[0].outcome, tuple(sorted({i for c in winners for i in c.application_ids})))
        self._record(binding, Stage.SET, merged)
        return merged.outcome

    def _clamp(self, binding: Binding, value: Quantity, candidates: list[_Candidate]) -> _Outcome:
        lowers = [c for c in candidates if c.operator is Operator.LOWER_BOUND]
        uppers = [c for c in candidates if c.operator is Operator.UPPER_BOUND]
        lower = max((c.outcome.value.value for c in lowers), default=None)
        upper = min((c.outcome.value.value for c in uppers), default=None)
        if lower is not None and upper is not None and lower > upper:
            ids = frozenset(i for c in candidates for i in c.application_ids)
            return _Conflict(frozenset({f"empty clamp interval on {binding.id}"}), ids)
        for bound, group in ((lower, lowers), (upper, uppers)):
            for candidate in group:
                if candidate.outcome.value.value == bound:
                    self._record(binding, Stage.CLAMP, candidate)
        number = value.value
        if lower is not None and number < lower:
            number = lower
        if upper is not None and number > upper:
            number = upper
        return _Known(Quantity(number, value.unit))

    def _record(self, binding: Binding, stage: Stage, candidate: _Candidate) -> None:
        self.contributions[binding.id].append(
            Contribution(stage, candidate.operator, candidate.outcome.value, candidate.application_ids))

    # --- stacking (§7) -------------------------------------------------------------------------

    def _stacked(self, binding: Binding, stage: Stage) -> list[_Candidate]:
        groups: dict[tuple[str, Operator], list] = defaultdict(list)
        for application, change in self.candidates.get((binding.id, stage), ()):
            groups[(application.stack_group_id, change.operator)].append((application, change))
        stacked: list[_Candidate] = []
        for (group_id, _operator), members in sorted(groups.items()):
            policies = {application.stack_policy for application, _ in members}
            if len(policies) > 1:
                stacked.append(_group_conflict(members, f"stack group {group_id} mixes policies {sorted(policies)}"))
                continue
            policy = policies.pop()
            if policy is StackPolicy.ALL:
                stacked.extend(self._candidate(binding, [member]) for member in members)
            elif policy is StackPolicy.HIGHEST:
                stacked.append(self._highest(binding, group_id, members))
            else:
                stacked.extend(self._by_source(binding, group_id, policy, members))
        return stacked

    def _by_source(self, binding: Binding, group_id: str, policy: StackPolicy, members: list) -> list[_Candidate]:
        by_source: dict[tuple[str, str], list] = defaultdict(list)
        for member in members:
            by_source[member[0].source_key].append(member)
        if policy is StackPolicy.EXCLUSIVE and len(by_source) > 1:
            choice = self.inputs.exclusive_choices.get(group_id)
            if choice not in by_source:
                return [_group_conflict(members, f"exclusive stack group {group_id} has {len(by_source)} active "
                                                 "sources and no explicit choice")]
            by_source = {choice: by_source[choice]}
        candidates = []
        for source in sorted(by_source):
            same = by_source[source]
            if len({change.payload_digest for _, change in same}) > 1:
                candidates.append(_group_conflict(same, f"source {source[0]}/{source[1]} applies differing payloads "
                                                        f"in stack group {group_id}"))
            else:
                candidates.append(self._candidate(binding, same))      # repeated identical payloads coalesce
        return candidates

    def _highest(self, binding: Binding, group_id: str, members: list) -> _Candidate:
        raw = [(member, self._formula(member[1].value)) for member in members]
        blocked = _blocking(outcome for _, outcome in raw)
        if blocked:
            return _Candidate(members[0][1].operator, _priority(members), blocked, _ids(members))
        if len({outcome.value.unit for _, outcome in raw}) > 1:
            return _group_conflict(members, f"stack group {group_id} (highest) mixes units")
        best = max(outcome.value.value for _, outcome in raw)
        winners = [member for member, outcome in raw if outcome.value.value == best]
        return self._normalized(binding, winners, _Known(next(o for _, o in raw if o.value.value == best).value))

    def _candidate(self, binding: Binding, members: list) -> _Candidate:
        return self._normalized(binding, members, self._formula(members[0][1].value))

    def _normalized(self, binding: Binding, members: list, outcome: _Outcome) -> _Candidate:
        operator = members[0][1].operator
        if isinstance(outcome, _Known):
            if operator is Operator.MULTIPLY:
                if not self.units.is_dimensionless(outcome.value.unit):
                    raise ContractViolation(SEMANTIC_INVALID, f"MULTIPLY factor on {binding.id} must be dimensionless")
                outcome = _Known(self.units.convert(outcome.value, self.units.base_unit(DIMENSIONLESS)))
            else:
                outcome = _Known(self.units.convert(outcome.value, binding.unit))
        return _Candidate(operator, _priority(members), outcome, _ids(members))

    # --- formulas and predicates ---------------------------------------------------------------

    def _formula(self, formula: Formula) -> _Outcome:
        self.fuel.charge()
        if isinstance(formula, Literal):
            self.units.unit(formula.value.unit)
            return _Known(formula.value)
        if isinstance(formula, Read):
            return self._stage(formula.binding_id, formula.stage)
        if isinstance(formula, Call):
            arguments = [self._formula(arg) for arg in formula.args]
            blocked = _blocking(arguments)
            if blocked:
                return blocked
            return _Known(CORE_FUNCTIONS[formula.function_id].apply(self.units, tuple(a.value for a in arguments)))
        condition = self._named(formula.condition)
        if condition is True:
            return self._formula(formula.then)
        if condition is False:
            return self._formula(formula.otherwise)
        return condition

    def _named(self, name: str) -> _Truth:
        if name not in self.named:
            self.named[name] = self._predicate(self.predicates[name])
        return self.named[name]

    def _predicate(self, predicate: Predicate) -> _Truth:
        self.fuel.charge()
        if isinstance(predicate, PredicateRef):
            return self._named(predicate.binding_id)
        if isinstance(predicate, (And, Or)):
            decisive = isinstance(predicate, Or)          # the value that short-circuits
            pending = []
            for arg in predicate.args:
                truth = self._predicate(arg)
                if truth is decisive:
                    return decisive
                if not isinstance(truth, bool):
                    pending.append(truth)
            return _blocking(pending) or (not decisive)
        if isinstance(predicate, Not):
            truth = self._predicate(predicate.arg)
            return (not truth) if isinstance(truth, bool) else truth
        if isinstance(predicate, Compare):
            left, right = self._formula(predicate.left), self._formula(predicate.right)
            blocked = _blocking((left, right))
            if blocked:
                return blocked
            right_value = self.units.convert(right.value, left.value.unit)
            return _COMPARE[predicate.operator](left.value.value, right_value.value)
        if isinstance(predicate, IsKnown):
            outcome = self._stage(predicate.binding_id, Stage.FINAL)
            return outcome if isinstance(outcome, _Conflict) else isinstance(outcome, _Known)
        if isinstance(predicate, Human):
            answer = self.inputs.human_answers.get((predicate.question_id, predicate.question_version,
                                                    predicate.responder_rule_id))
            if isinstance(answer, bool):
                return answer
            return _Unknown(frozenset({f"decision {predicate.question_id}@{predicate.question_version} is unanswered"}))
        toggle = self.inputs.manual_toggles.get(predicate.toggle_id)
        return toggle if isinstance(toggle, bool) else _Unknown(frozenset({f"manual toggle {predicate.toggle_id} is not set"}))

    # --- results -------------------------------------------------------------------------------

    def _result(self, binding_id: str) -> BindingResult:
        final = self._stage(binding_id, Stage.FINAL)
        stage_values = tuple((stage, outcome.value if isinstance(outcome := self.memo[(binding_id, stage)], _Known) else None)
                             for stage in STAGES)
        contributions = tuple(sorted(self.contributions[binding_id],
                                     key=lambda c: (STAGES.index(c.stage), c.operator.value, c.application_ids)))
        if isinstance(final, _Known):
            return BindingResult(binding_id, "resolved", final.value, stage_values, contributions, (), ())
        if isinstance(final, _Unknown):
            return BindingResult(binding_id, "unresolved", None, stage_values, contributions, tuple(sorted(final.reasons)), ())
        return BindingResult(binding_id, "conflict", None, stage_values, contributions,
                             tuple(sorted(final.reasons)), tuple(sorted(final.application_ids)))


def _ids(members: list) -> tuple[str, ...]:
    return tuple(sorted(application.application_id for application, _ in members))


def _priority(members: list) -> int:
    return max(application.priority for application, _ in members)


def _group_conflict(members: list, reason: str) -> _Candidate:
    return _Candidate(members[0][1].operator, _priority(members),
                      _Conflict(frozenset({reason}), frozenset(_ids(members))), _ids(members))


def _find_cycle(edges: Mapping[tuple, set[tuple]]) -> list[tuple] | None:
    """Iterative depth-first search; returns one cycle as a node path, or None."""
    state: dict[tuple, int] = {}                  # 1 = on the current path, 2 = finished
    for root in sorted(edges, key=repr):
        if root in state:
            continue
        path: list[tuple] = [root]
        iterators = [iter(sorted(edges.get(root, ()), key=repr))]
        state[root] = 1
        while iterators:
            nxt = next(iterators[-1], None)
            if nxt is None:
                state[path.pop()] = 2
                iterators.pop()
            elif state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            elif nxt not in state:
                state[nxt] = 1
                path.append(nxt)
                iterators.append(iter(sorted(edges.get(nxt, ()), key=repr)))
    return None
