"""Deterministic work accounting (spec v1.1.4 §18).

Every executed literal, read, function call, conditional and predicate node
charges one operation. The budget is cumulative across one checkpoint and is
never restarted for nested or retried work; exceeding it is BUDGET_EXCEEDED.
"""

from vtt.creation_engine.errors import BudgetExceeded

CHECKPOINT_OPERATIONS = 100_000
ROOT_ACTION_OPERATIONS = 1_000_000


class Fuel:
    def __init__(self, limit: int = CHECKPOINT_OPERATIONS):
        self.limit = limit
        self.used = 0

    def charge(self, operations: int = 1) -> None:
        self.used += operations
        if self.used > self.limit:
            raise BudgetExceeded(f"evaluation exceeded {self.limit} primitive operations")
