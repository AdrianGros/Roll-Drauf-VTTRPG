"""Collect go/no-go evidence from operational endpoints."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


def _fetch(base_url: str, path: str):
    url = f"{base_url.rstrip('/')}{path}"
    # Fixed 2026-09-04: /health/ready, /health/release, and /metrics now
    # require either a logged-in admin session or this shared token
    # (vtt/ops/routes.py's _ops_access_allowed) -- this script has no
    # user session, so it authenticates via OPS_ACCESS_TOKEN, the same
    # env var the server reads. Unset on both sides = still open only to
    # an admin session, same as before this env var existed.
    req = request.Request(url)
    ops_token = os.getenv("OPS_ACCESS_TOKEN")
    if ops_token:
        req.add_header("X-Ops-Token", ops_token)
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body, None
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body, str(exc)
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        return 0, "", str(exc)


def _parse_json(raw_text: str):
    try:
        return json.loads(raw_text)
    except Exception:
        return None


def main() -> int:
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = Path(os.getenv("RELEASE_EVIDENCE_OUT", f"ops/monitor/evidence/release_gate_{timestamp}.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    live_status, live_body, live_error = _fetch(base_url, "/health/live")
    ready_status, ready_body, ready_error = _fetch(base_url, "/health/ready")
    release_status, release_body, release_error = _fetch(base_url, "/health/release")
    metrics_status, metrics_body, metrics_error = _fetch(base_url, "/metrics")

    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "checks": {
            "health_live": {
                "status_code": live_status,
                "ok": live_status == 200,
                "error": live_error,
                "payload": _parse_json(live_body),
            },
            "health_ready": {
                "status_code": ready_status,
                "ok": ready_status == 200,
                "error": ready_error,
                "payload": _parse_json(ready_body),
            },
            "health_release": {
                "status_code": release_status,
                "ok": release_status == 200,
                "error": release_error,
                "payload": _parse_json(release_body),
            },
            "metrics": {
                "status_code": metrics_status,
                "ok": metrics_status == 200,
                "error": metrics_error,
                "contains_requests_total": "vtt_requests_total" in metrics_body,
                "contains_socket_events": "vtt_socket_events_total" in metrics_body,
                "contains_play_transitions": "vtt_play_transitions_total" in metrics_body,
            },
        },
    }
    payload["release_gate_pass"] = bool(payload["checks"]["health_release"]["ok"])

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[release-gate-evidence] wrote {output_path}")
    print(f"[release-gate-evidence] release_gate_pass={payload['release_gate_pass']}")
    return 0 if payload["release_gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

