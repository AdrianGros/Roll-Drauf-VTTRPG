"""Realtime sequencing helpers shared across socket and REST emitters."""

from collections import defaultdict
from threading import Lock

from vtt_app.utils.time import utcnow

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


def build_event_envelope(campaign_id: int, session_id: int, payload: dict | None = None, advance: bool = True) -> dict:
    body = dict(payload or {})
    seq = next_event_seq(campaign_id, session_id) if advance else current_event_seq(campaign_id, session_id)
    body["campaign_id"] = campaign_id
    body["session_id"] = session_id
    body["event_seq"] = seq
    body["server_time"] = utcnow().isoformat()
    return body
