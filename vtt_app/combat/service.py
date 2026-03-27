"""Combat service functions for encounter lifecycle and state transitions."""

from __future__ import annotations

import random

from sqlalchemy import func

from vtt_app.extensions import db
from vtt_app.models import Character, CombatEncounter, CombatEvent, TokenState
from vtt_app.utils.time import utcnow


def _ordered_tokens_for_encounter(encounter: CombatEncounter) -> list[TokenState]:
    token_ids = [int(token_id) for token_id in (encounter.initiative_order_json or [])]
    if not token_ids:
        return []

    token_rows = (
        TokenState.query.filter(TokenState.id.in_(token_ids))
        .filter(TokenState.deleted_at.is_(None))
        .all()
    )
    token_by_id = {token.id: token for token in token_rows}
    return [token_by_id[token_id] for token_id in token_ids if token_id in token_by_id]


def _next_event_sequence(encounter_id: int) -> int:
    max_seq = db.session.query(func.max(CombatEvent.sequence_no)).filter_by(encounter_id=encounter_id).scalar()
    return int(max_seq or 0) + 1


def append_event(
    encounter: CombatEncounter,
    event_type: str,
    created_by: int,
    payload: dict | None = None,
    actor_token_id: int | None = None,
    target_token_id: int | None = None,
) -> CombatEvent:
    event = CombatEvent(
        encounter_id=encounter.id,
        sequence_no=_next_event_sequence(encounter.id),
        event_type=event_type,
        actor_token_id=actor_token_id,
        target_token_id=target_token_id,
        payload_json=payload or {},
        created_by=created_by,
    )
    db.session.add(event)
    return event


def get_active_encounter(game_session_id: int) -> CombatEncounter | None:
    return (
        CombatEncounter.query.filter_by(game_session_id=game_session_id)
        .filter(CombatEncounter.status.in_(["preparing", "active", "paused"]))
        .order_by(CombatEncounter.created_at.desc())
        .first()
    )


def get_latest_encounter(game_session_id: int) -> CombatEncounter | None:
    return (
        CombatEncounter.query.filter_by(game_session_id=game_session_id)
        .order_by(CombatEncounter.created_at.desc())
        .first()
    )


def _is_defeated(token: TokenState) -> bool:
    return token.hp_current is not None and token.hp_current <= 0


def _determine_active_token(order_tokens: list[TokenState], start_index: int = 0) -> tuple[int | None, int]:
    if not order_tokens:
        return None, 0

    normalized_start = max(0, int(start_index))
    if normalized_start >= len(order_tokens):
        normalized_start = 0

    for offset in range(len(order_tokens)):
        idx = (normalized_start + offset) % len(order_tokens)
        token = order_tokens[idx]
        if not _is_defeated(token):
            return token.id, idx

    return None, normalized_start


def _dex_modifier(character: Character | None) -> int:
    if not character:
        return 0
    return int(character.get_dex_mod())


def _resolve_participants(session_state_id: int, map_id: int, participant_token_ids: list[int] | None) -> list[TokenState]:
    query = (
        TokenState.query.filter_by(session_state_id=session_state_id, map_id=map_id)
        .filter(TokenState.deleted_at.is_(None))
        .filter(TokenState.token_type.in_(["player", "npc", "monster"]))
    )
    tokens = query.order_by(TokenState.id.asc()).all()
    if not participant_token_ids:
        return tokens

    wanted = {int(token_id) for token_id in participant_token_ids}
    return [token for token in tokens if token.id in wanted]


def _build_order(tokens: list[TokenState]) -> list[int]:
    sorted_tokens = sorted(tokens, key=lambda token: (int(token.initiative or 0), -int(token.id)), reverse=True)
    return [token.id for token in sorted_tokens]


def start_encounter(
    campaign_id: int,
    game_session_id: int,
    session_state_id: int,
    active_map_id: int,
    user_id: int,
    mode: str = "auto",
    participant_token_ids: list[int] | None = None,
) -> tuple[CombatEncounter | None, str | None]:
    participants = _resolve_participants(session_state_id, active_map_id, participant_token_ids)
    if not participants:
        return None, "no eligible combat participants found"

    normalized_mode = str(mode or "auto").strip().lower()
    if normalized_mode not in {"auto", "manual"}:
        return None, "invalid combat mode"

    if normalized_mode == "auto":
        for token in participants:
            dex_mod = _dex_modifier(token.character)
            token.initiative = random.randint(1, 20) + dex_mod
            token.updated_by = user_id
            token.version = int(token.version or 1) + 1
    else:
        for token in participants:
            if token.initiative is None:
                token.initiative = 0

    order = _build_order(participants)
    ordered_participants = sorted(participants, key=lambda token: order.index(token.id))
    active_token_id, turn_index = _determine_active_token(ordered_participants, 0)

    encounter = CombatEncounter(
        campaign_id=campaign_id,
        game_session_id=game_session_id,
        session_state_id=session_state_id,
        status="active",
        round_number=1,
        turn_index=turn_index,
        active_token_id=active_token_id,
        initiative_order_json=order,
        version=1,
        started_by=user_id,
        started_at=utcnow(),
    )
    db.session.add(encounter)
    db.session.flush()

    append_event(
        encounter=encounter,
        event_type="start",
        created_by=user_id,
        payload={
            "mode": normalized_mode,
            "order": order,
            "active_token_id": active_token_id,
            "round_number": 1,
        },
    )
    return encounter, None


def set_initiative(encounter: CombatEncounter, entries: list[dict], user_id: int) -> str | None:
    if not entries:
        return "initiative entries required"

    token_ids = [int(entry.get("token_id")) for entry in entries if entry.get("token_id") is not None]
    if not token_ids:
        return "initiative entries required"

    tokens = (
        TokenState.query.filter(TokenState.id.in_(token_ids))
        .filter_by(game_session_id=encounter.game_session_id)
        .filter(TokenState.deleted_at.is_(None))
        .all()
    )
    token_by_id = {token.id: token for token in tokens}

    for entry in entries:
        token_id = int(entry.get("token_id"))
        token = token_by_id.get(token_id)
        if not token:
            return "initiative token not found in encounter session"
        token.initiative = int(entry.get("initiative"))
        token.updated_by = user_id
        token.version = int(token.version or 1) + 1

    ordered_tokens = _ordered_tokens_for_encounter(encounter)
    touched_ids = {token.id for token in tokens}
    for token in tokens:
        if token.id not in [existing.id for existing in ordered_tokens]:
            ordered_tokens.append(token)
    ordered_tokens = [token for token in ordered_tokens if token.id in touched_ids or token.id in (encounter.initiative_order_json or [])]

    order = _build_order(ordered_tokens)
    ordered_rows = (
        TokenState.query.filter(TokenState.id.in_(order))
        .filter(TokenState.deleted_at.is_(None))
        .all()
    )
    by_id = {token.id: token for token in ordered_rows}
    active_token_id, turn_index = _determine_active_token([by_id[token_id] for token_id in order if token_id in by_id], encounter.turn_index)

    encounter.initiative_order_json = order
    encounter.turn_index = turn_index
    encounter.active_token_id = active_token_id
    encounter.version += 1

    append_event(
        encounter=encounter,
        event_type="initiative_set",
        created_by=user_id,
        payload={"entries": entries, "order": order, "active_token_id": active_token_id},
    )
    return None


def advance_turn(encounter: CombatEncounter, user_id: int) -> str | None:
    order_tokens = _ordered_tokens_for_encounter(encounter)
    if not order_tokens:
        return "encounter has no active participants"

    next_index = encounter.turn_index + 1
    wrapped = next_index >= len(order_tokens)
    if wrapped:
        next_index = 0

    active_token_id, resolved_index = _determine_active_token(order_tokens, next_index)
    if wrapped and active_token_id is not None:
        encounter.round_number += 1

    encounter.turn_index = resolved_index
    encounter.active_token_id = active_token_id
    encounter.version += 1

    append_event(
        encounter=encounter,
        event_type="turn_advanced",
        created_by=user_id,
        payload={
            "round_number": encounter.round_number,
            "turn_index": encounter.turn_index,
            "active_token_id": encounter.active_token_id,
        },
    )
    return None


def _resolve_hp_max(token: TokenState) -> int | None:
    if token.hp_max is not None:
        return int(token.hp_max)
    if token.character and token.character.hp_max is not None:
        return int(token.character.hp_max)
    return None


def adjust_hp(encounter: CombatEncounter, target_token_id: int, delta: int, reason: str | None, user_id: int) -> tuple[TokenState | None, str | None]:
    token = (
        TokenState.query.filter_by(id=target_token_id, game_session_id=encounter.game_session_id)
        .filter(TokenState.deleted_at.is_(None))
        .first()
    )
    if not token:
        return None, "target token not found"

    hp_max = _resolve_hp_max(token)
    current = int(token.hp_current or 0)
    updated = current + int(delta)
    if hp_max is not None:
        updated = min(updated, hp_max)
    updated = max(updated, 0)

    token.hp_current = updated
    if token.hp_max is None and hp_max is not None:
        token.hp_max = hp_max
    token.updated_by = user_id
    token.version = int(token.version or 1) + 1

    if token.character:
        token.character.hp_current = updated
        if hp_max is not None:
            token.character.hp_max = hp_max

    order_tokens = _ordered_tokens_for_encounter(encounter)
    active_token_id, resolved_index = _determine_active_token(order_tokens, encounter.turn_index)
    encounter.active_token_id = active_token_id
    encounter.turn_index = resolved_index
    encounter.version += 1

    append_event(
        encounter=encounter,
        event_type="hp_adjusted",
        created_by=user_id,
        payload={
            "target_token_id": token.id,
            "delta": int(delta),
            "reason": reason,
            "hp_current": updated,
            "hp_max": token.hp_max,
        },
        target_token_id=token.id,
    )
    return token, None


def end_encounter(encounter: CombatEncounter, user_id: int) -> None:
    encounter.status = "completed"
    encounter.ended_by = user_id
    encounter.ended_at = utcnow()
    encounter.version += 1

    append_event(
        encounter=encounter,
        event_type="end",
        created_by=user_id,
        payload={"ended_at": encounter.ended_at.isoformat() if encounter.ended_at else None},
    )


def serialize_encounter_payload(encounter: CombatEncounter | None, include_events: bool = True) -> dict:
    if not encounter:
        return {"encounter": None, "participants": [], "events": []}

    participants = _ordered_tokens_for_encounter(encounter)
    events_payload = []
    if include_events:
        events_payload = [event.serialize() for event in sorted(encounter.events, key=lambda row: row.sequence_no)]

    return {
        "encounter": encounter.serialize(),
        "participants": [token.serialize() for token in participants],
        "events": events_payload,
    }
