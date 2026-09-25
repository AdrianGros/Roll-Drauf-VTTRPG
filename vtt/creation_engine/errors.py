"""Error types with the stable codes of spec v1.1.4 §17 / §18.

Contract violations carry the client-facing code; transports map codes to
HTTP status in one place (registry addendum A1 §7.4). Arithmetic faults are
evaluator-internal and fail the checkpoint that raised them (§9).
"""

SCHEMA_INVALID = "SCHEMA_INVALID"
SEMANTIC_INVALID = "SEMANTIC_INVALID"
BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
EFFECT_CONFLICT = "EFFECT_CONFLICT"
DRAFT_VERSION_CONFLICT = "DRAFT_VERSION_CONFLICT"   # registry addendum A1 §5


class ContractViolation(Exception):
    """A wire or content value breaks the contract."""

    def __init__(self, code: str, detail: str, *, path: tuple[str | int, ...] = ()):
        super().__init__(f"{code}: {detail}" + (f" at {'/'.join(map(str, path))}" if path else ""))
        self.code = code
        self.detail = detail
        self.path = path


class BudgetExceeded(ContractViolation):
    """A deterministic limit of the core-safe-1 profile was exceeded (§18)."""

    def __init__(self, detail: str, *, path: tuple[str | int, ...] = ()):
        super().__init__(BUDGET_EXCEEDED, detail, path=path)


class ArithmeticFault(Exception):
    """Exact arithmetic cannot produce a value, e.g. division by zero (§6: never NaN)."""
