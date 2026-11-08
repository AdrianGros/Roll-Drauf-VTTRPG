"""Server-side trap resolution for session token movement."""

from __future__ import annotations

import math

from vtt.dice import roll_dice
from vtt.models import TokenState
from vtt.utils.time import utcnow

SCHABERNACKS_TRAP_KIND = "schabernacks_trap"
SCHABERNACKS_TRAP_NAME = "schabernacks trap"
SCHABERNACKS_TRIGGER_RANGE = 280
SCHABERNACKS_VOLLEY_COUNT = 5
SCHABERNACKS_DAMAGE_DICE = "1d4"
SCHABERNACKS_DAMAGE_TYPE = "poison"
SCHABERNACKS_CONDITION = "poisoned"
DEFAULT_TARGET_TOKEN_TYPES = frozenset({"player"})


def _normalized_name(value) -> str:
    return " ".join(str(value or "").strip().casefold().replace("-", " ").split())


def _trap_config(token: TokenState) -> dict | None:
    metadata = token.metadata_json if isinstance(token.metadata_json, dict) else {}
    configured = metadata.get("trap")
    if isinstance(configured, dict):
        kind = str(configured.get("kind", "")).strip().lower()
        if kind == SCHABERNACKS_TRAP_KIND:
            return dict(configured)

    # Existing Goblin Brawl object tokens may have been created before trap
    # metadata existed. Keep the named encounter object usable without a
    # migration, while still requiring the exact trap name.
    if token.token_type == "object" and _normalized_name(token.name) == SCHABERNACKS_TRAP_NAME:
        return {"kind": SCHABERNACKS_TRAP_KIND}
    return None


def _trigger_range(config: dict) -> int:
    try:
        configured = int(config.get("trigger_range", SCHABERNACKS_TRIGGER_RANGE))
    except (TypeError, ValueError):
        configured = SCHABERNACKS_TRIGGER_RANGE
    return max(SCHABERNACKS_TRIGGER_RANGE, configured)


def _target_token_types(config: dict) -> frozenset[str]:
    raw_types = config.get("target_token_types", DEFAULT_TARGET_TOKEN_TYPES)
    if not isinstance(raw_types, (list, tuple, set, frozenset)):
        return DEFAULT_TARGET_TOKEN_TYPES
    supported = {"player", "npc", "monster"}
    target_types = {str(value).strip().lower() for value in raw_types} & supported
    return frozenset(target_types) or DEFAULT_TARGET_TOKEN_TYPES


def _within_range(origin: TokenState, target: TokenState, trigger_range: int) -> bool:
    return math.hypot(float(origin.x) - float(target.x), float(origin.y) - float(target.y)) <= trigger_range


def _is_live_target(token: TokenState, trap: TokenState, target_types: frozenset[str]) -> bool:
    if token.id == trap.id or token.deleted_at is not None:
        return False
    if token.token_type not in target_types:
        return False
    return token.hp_current is not None and int(token.hp_current) > 0


def _apply_poison_dart(token: TokenState, updated_by: int) -> dict:
    roll = roll_dice(SCHABERNACKS_DAMAGE_DICE)
    damage = int(roll.get("total", 1)) if isinstance(roll, dict) else 1
    damage = max(1, damage)

    token.hp_current = max(0, int(token.hp_current or 0) - damage)
    metadata = dict(token.metadata_json) if isinstance(token.metadata_json, dict) else {}
    conditions = metadata.get("conditions")
    if not isinstance(conditions, list):
        conditions = []
    normalized_conditions = [str(condition).strip().lower() for condition in conditions]
    if SCHABERNACKS_CONDITION not in normalized_conditions:
        normalized_conditions.append(SCHABERNACKS_CONDITION)
    metadata["conditions"] = normalized_conditions
    token.metadata_json = metadata
    token.updated_by = updated_by
    token.version = int(token.version or 1) + 1

    return {
        "token_id": token.id,
        "damage": damage,
        "damage_type": SCHABERNACKS_DAMAGE_TYPE,
        "condition": SCHABERNACKS_CONDITION,
        "hp_current": token.hp_current,
        "roll": roll,
    }


def trigger_schabernacks_traps(moved_token: TokenState, updated_by: int) -> list[dict]:
    """Resolve named Schabernacks traps when a token enters their range.

    The caller must invoke this before committing the movement transaction.
    Each matching trap fires five immediate volleys at all live configured
    enemy tokens in range, applies one 1d4 poison dart per volley, and is then
    soft-deleted so retries cannot fire it again.
    """
    if not moved_token or moved_token.deleted_at is not None:
        return []

    tokens = (
        TokenState.query.filter_by(
            session_state_id=moved_token.session_state_id,
            game_session_id=moved_token.game_session_id,
            map_id=moved_token.map_id,
        )
        .filter(TokenState.deleted_at.is_(None))
        .all()
    )
    trap_results = []
    for trap in tokens:
        config = _trap_config(trap)
        if not config or trap.id == moved_token.id:
            continue

        trigger_range = _trigger_range(config)
        if not _within_range(trap, moved_token, trigger_range):
            continue

        target_types = _target_token_types(config)
        volleys = []
        target_ids = set()
        for volley_number in range(1, SCHABERNACKS_VOLLEY_COUNT + 1):
            targets = []
            for target in tokens:
                if (
                    _is_live_target(target, trap, target_types)
                    and _within_range(trap, target, trigger_range)
                ):
                    target_result = _apply_poison_dart(target, updated_by)
                    targets.append(target_result)
                    target_ids.add(target.id)
            volleys.append({"volley": volley_number, "targets": targets})

        trap.deleted_at = utcnow()
        trap.updated_by = updated_by
        trap.version = int(trap.version or 1) + 1
        trap_results.append(
            {
                "trap_id": trap.id,
                "trap_name": trap.name,
                "kind": SCHABERNACKS_TRAP_KIND,
                "triggering_token_id": moved_token.id,
                "trigger_range": trigger_range,
                "damage_dice": SCHABERNACKS_DAMAGE_DICE,
                "volleys": volleys,
                "target_token_ids": sorted(target_ids),
                "disappeared": True,
            }
        )

    return trap_results
