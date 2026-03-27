"""Action catalog and execution helpers for play runtime v1."""

from __future__ import annotations

from vtt_app.utils.time import utcnow


ACTION_CATALOG = [
    {
        "code": "attack_basic",
        "name": "Attack",
        "category": "combat",
        "requires_target": True,
        "suggested_roll": "1d20+5",
        "description": "Basic attack action with explicit roll.",
    },
    {
        "code": "dash_move",
        "name": "Dash",
        "category": "movement",
        "requires_target": False,
        "suggested_roll": None,
        "description": "Use extra movement this turn.",
    },
    {
        "code": "interact_object",
        "name": "Interact",
        "category": "utility",
        "requires_target": False,
        "suggested_roll": None,
        "description": "Interact with an object or scene element.",
    },
]

ACTION_BY_CODE = {entry["code"]: entry for entry in ACTION_CATALOG}


def get_action_catalog():
    """Return action definitions for the frontend action bar."""
    return ACTION_CATALOG


def execute_action(action_code: str, token_id: int, actor_user_id: int, target_token_id: int | None = None, payload: dict | None = None):
    """Return deterministic action execution envelope."""
    action = ACTION_BY_CODE.get(action_code)
    if not action:
        return None, {"code": "bad_request", "message": "unknown action_code"}

    if action["requires_target"] and not target_token_id:
        return None, {"code": "bad_request", "message": "target_token_id required for this action"}

    result = {
        "action_code": action["code"],
        "token_id": token_id,
        "actor_user_id": actor_user_id,
        "target_token_id": target_token_id,
        "payload": payload or {},
        "suggested_roll": action["suggested_roll"],
        "executed_at": utcnow().isoformat(),
    }
    return result, None
