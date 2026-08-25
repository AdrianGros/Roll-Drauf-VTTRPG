"""Realtime sequencing helpers shared across socket and REST emitters."""

from collections import defaultdict
from threading import Lock

from vtt.utils.time import utcnow

_event_seq = defaultdict(int)
_event_lock = Lock()


def current_event_seq(campaign_id: int, session_id: int) -> int:
    key = (campaign_id, session_id)
    with _event_lock:
        return int(_event_seq.get(key, 0))


def next_event_seq(campaign_id: int, session_id: int) -> int:
    key = (campaign_id, session_id)
    with _event_lock:
        _event_seq[key] = int(_event_seq.get(key, 0)) + 1
        return _event_seq[key]


def session_room(campaign_id: int, session_id: int) -> str:
    return f"campaign:{campaign_id}:session:{session_id}"


def dm_room(campaign_id: int, session_id: int) -> str:
    """Operators (DM/CO_DM) only — receives unfiltered state broadcasts."""
    return f"{session_room(campaign_id, session_id)}:dm"


def players_room(campaign_id: int, session_id: int) -> str:
    """Players and observers — receives role-filtered state broadcasts."""
    return f"{session_room(campaign_id, session_id)}:players"


def user_room(campaign_id: int, session_id: int, user_id: int) -> str:
    """Single-user targeting inside a session (owner_only token events)."""
    return f"{session_room(campaign_id, session_id)}:user:{user_id}"


def sibling_envelope(envelope: dict, payload: dict | None) -> dict:
    """A second audience's variant of an already-advanced envelope: same
    event_seq/server_time, different payload — one logical mutation must
    never advance the sequence twice."""
    body = dict(payload or {})
    for key in ("campaign_id", "session_id", "event_seq", "server_time"):
        body[key] = envelope[key]
    return body


def build_event_envelope(campaign_id: int, session_id: int, payload: dict | None = None, advance: bool = True) -> dict:
    body = dict(payload or {})
    seq = next_event_seq(campaign_id, session_id) if advance else current_event_seq(campaign_id, session_id)
    body["campaign_id"] = campaign_id
    body["session_id"] = session_id
    body["event_seq"] = seq
    body["server_time"] = utcnow().isoformat()
    return body
