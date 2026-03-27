"""Operational readiness and metrics endpoints."""

import os

from flask import Response, current_app, jsonify
from sqlalchemy import text

from vtt_app.extensions import db
from vtt_app.extensions import limiter
from vtt_app.ops import ops_bp
from vtt_app.utils.time import utcnow


def _iso(ts):
    return ts.isoformat() if ts else None


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rate(count, total):
    return float(count) / float(total) if total > 0 else 0.0


def _sum_prefixed_status(status_map, prefix):
    total = 0
    for key, value in (status_map or {}).items():
        if str(key).startswith(prefix):
            total += _safe_int(value)
    return total


def _check_required_files():
    require_files = bool(current_app.config.get("RELEASE_GATE_REQUIRE_RUNBOOKS", False))
    configured_files = current_app.config.get("RELEASE_GATE_REQUIRED_FILES", ()) or ()

    checked = []
    missing = []
    if not require_files:
        return True, checked, missing

    project_root = os.path.abspath(os.path.join(current_app.root_path, os.pardir))
    for file_path in configured_files:
        relative = str(file_path).replace("\\", "/")
        absolute = os.path.abspath(os.path.join(project_root, relative))
        exists = os.path.exists(absolute)
        checked.append({"path": relative, "exists": exists})
        if not exists:
            missing.append(relative)

    return len(missing) == 0, checked, missing


def _check_database():
    try:
        db.session.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # pragma: no cover - depends on runtime infra
        return False, str(exc)


def _check_redis():
    redis_url = current_app.config.get("REDIS_URL")
    if not redis_url:
        return True, "not_configured"

    try:
        import redis  # type: ignore
    except Exception:
        return False, "redis dependency unavailable"

    try:
        client = redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return True, "ok"
    except Exception as exc:  # pragma: no cover - depends on runtime infra
        return False, str(exc)


@ops_bp.route("/health/live", methods=["GET"])
@limiter.exempt
def health_live():
    """Liveness probe endpoint."""
    started_at = current_app.extensions.get("ops_started_at")
    return jsonify(
        {
            "status": "ok",
            "service": "roll_drauf_vtt",
            "started_at": _iso(started_at),
            "now": _iso(utcnow()),
        }
    ), 200


@ops_bp.route("/health/ready", methods=["GET"])
@limiter.exempt
def health_ready():
    """Readiness probe endpoint with dependency checks."""
    db_ok, db_message = _check_database()
    redis_ok, redis_message = _check_redis()

    ready = db_ok and redis_ok
    payload = {
        "status": "ready" if ready else "degraded",
        "dependencies": {
            "database": {"ok": db_ok, "message": db_message},
            "redis": {"ok": redis_ok, "message": redis_message},
        },
        "now": _iso(utcnow()),
    }
    return jsonify(payload), (200 if ready else 503)


@ops_bp.route("/health/release", methods=["GET"])
@limiter.exempt
def health_release():
    """Go/no-go release gate based on operational thresholds."""
    db_ok, db_message = _check_database()
    redis_ok, redis_message = _check_redis()
    dependencies_ok = db_ok and redis_ok

    store = current_app.extensions.get("ops_metrics", {})
    started_at = current_app.extensions.get("ops_started_at")
    uptime_seconds = max((utcnow() - started_at).total_seconds(), 0.0) if started_at else 0.0

    total_requests = _safe_int(store.get("requests_total", 0))
    by_status = store.get("by_status", {})
    latency_buckets_ms = store.get("latency_buckets_ms", {})
    socket_total = _safe_int(store.get("socket_events_total", 0))
    socket_resync_total = _safe_int(store.get("socket_resync_requests_total", 0))
    socket_conflict_total = _safe_int(store.get("socket_conflicts_total", 0))

    min_uptime_seconds = _safe_int(current_app.config.get("RELEASE_GATE_MIN_UPTIME_SECONDS", 0))
    min_requests = _safe_int(current_app.config.get("RELEASE_GATE_MIN_REQUESTS", 0))
    max_5xx_rate = _safe_float(current_app.config.get("RELEASE_GATE_MAX_5XX_RATE", 0.05))
    max_slow_request_rate = _safe_float(current_app.config.get("RELEASE_GATE_MAX_SLOW_REQUEST_RATE", 0.10))
    max_socket_resync_rate = _safe_float(current_app.config.get("RELEASE_GATE_MAX_SOCKET_RESYNC_RATE", 0.20))
    max_socket_conflict_rate = _safe_float(current_app.config.get("RELEASE_GATE_MAX_SOCKET_CONFLICT_RATE", 0.30))

    five_xx_total = _sum_prefixed_status(by_status, "5")
    slow_requests_total = _safe_int(latency_buckets_ms.get("gt_500", 0))

    five_xx_rate = _rate(five_xx_total, total_requests)
    slow_request_rate = _rate(slow_requests_total, total_requests)
    socket_resync_rate = _rate(socket_resync_total, socket_total)
    socket_conflict_rate = _rate(socket_conflict_total, socket_total)

    files_ok, checked_files, missing_files = _check_required_files()

    checks = {
        "dependencies": {
            "ok": dependencies_ok,
            "database_ok": db_ok,
            "database_message": db_message,
            "redis_ok": redis_ok,
            "redis_message": redis_message,
        },
        "uptime": {
            "ok": uptime_seconds >= min_uptime_seconds,
            "value_seconds": round(uptime_seconds, 3),
            "min_seconds": min_uptime_seconds,
        },
        "request_volume": {
            "ok": total_requests >= min_requests,
            "total_requests": total_requests,
            "min_requests": min_requests,
        },
        "error_budget": {
            "ok": five_xx_rate <= max_5xx_rate,
            "value_rate": round(five_xx_rate, 6),
            "max_rate": max_5xx_rate,
            "five_xx_total": five_xx_total,
            "total_requests": total_requests,
        },
        "latency_budget": {
            "ok": slow_request_rate <= max_slow_request_rate,
            "value_rate": round(slow_request_rate, 6),
            "max_rate": max_slow_request_rate,
            "slow_requests_total": slow_requests_total,
            "total_requests": total_requests,
        },
        "socket_resync_budget": {
            "ok": socket_resync_rate <= max_socket_resync_rate,
            "value_rate": round(socket_resync_rate, 6),
            "max_rate": max_socket_resync_rate,
            "resync_total": socket_resync_total,
            "socket_total": socket_total,
        },
        "socket_conflict_budget": {
            "ok": socket_conflict_rate <= max_socket_conflict_rate,
            "value_rate": round(socket_conflict_rate, 6),
            "max_rate": max_socket_conflict_rate,
            "conflict_total": socket_conflict_total,
            "socket_total": socket_total,
        },
        "rollback_runbooks": {
            "ok": files_ok,
            "required": bool(current_app.config.get("RELEASE_GATE_REQUIRE_RUNBOOKS", False)),
            "checked_files": checked_files,
            "missing_files": missing_files,
        },
    }

    release_ready = all(item.get("ok", False) for item in checks.values())
    payload = {
        "status": "go" if release_ready else "no-go",
        "release_ready": release_ready,
        "checks": checks,
        "now": _iso(utcnow()),
    }
    return jsonify(payload), (200 if release_ready else 503)


@ops_bp.route("/metrics", methods=["GET"])
@limiter.exempt
def metrics():
    """Minimal Prometheus-style metrics endpoint."""
    if not current_app.config.get("METRICS_ENABLED", True):
        return Response("metrics_disabled 1\n", mimetype="text/plain; version=0.0.4")

    store = current_app.extensions.get("ops_metrics", {})
    started_at = current_app.extensions.get("ops_started_at")
    uptime_seconds = 0.0
    if started_at:
        uptime_seconds = max((utcnow() - started_at).total_seconds(), 0.0)

    total = int(store.get("requests_total", 0))
    by_status = store.get("by_status", {})
    by_path = store.get("by_path", {})
    by_route = store.get("by_route", {})
    latency_buckets_ms = store.get("latency_buckets_ms", {})
    socket_total = int(store.get("socket_events_total", 0))
    socket_by_name = store.get("socket_events_by_name", {})
    socket_conflicts_total = int(store.get("socket_conflicts_total", 0))
    socket_resync_requests_total = int(store.get("socket_resync_requests_total", 0))
    socket_reconnect_recoveries_total = int(store.get("socket_reconnect_recoveries_total", 0))
    play_total = int(store.get("play_transitions_total", 0))
    play_by_target = store.get("play_transitions_by_target", {})

    lines = [
        "# HELP vtt_requests_total Total HTTP requests served.",
        "# TYPE vtt_requests_total counter",
        f"vtt_requests_total {total}",
        "# HELP vtt_uptime_seconds Process uptime in seconds.",
        "# TYPE vtt_uptime_seconds gauge",
        f"vtt_uptime_seconds {uptime_seconds:.3f}",
    ]

    lines.append("# HELP vtt_requests_by_status_total HTTP requests grouped by status code.")
    lines.append("# TYPE vtt_requests_by_status_total counter")
    for status_code in sorted(by_status.keys()):
        lines.append(f'vtt_requests_by_status_total{{status="{status_code}"}} {by_status[status_code]}')

    lines.append("# HELP vtt_requests_by_path_total HTTP requests grouped by route path.")
    lines.append("# TYPE vtt_requests_by_path_total counter")
    for path in sorted(by_path.keys()):
        safe_path = str(path).replace('"', '\\"')
        lines.append(f'vtt_requests_by_path_total{{path="{safe_path}"}} {by_path[path]}')

    lines.append("# HELP vtt_requests_by_route_total HTTP requests grouped by normalized route.")
    lines.append("# TYPE vtt_requests_by_route_total counter")
    for route in sorted(by_route.keys()):
        safe_route = str(route).replace('"', '\\"')
        lines.append(f'vtt_requests_by_route_total{{route="{safe_route}"}} {by_route[route]}')

    lines.append("# HELP vtt_request_latency_bucket_total Request latency buckets in milliseconds.")
    lines.append("# TYPE vtt_request_latency_bucket_total counter")
    for bucket_name in sorted(latency_buckets_ms.keys()):
        lines.append(f'vtt_request_latency_bucket_total{{bucket="{bucket_name}"}} {latency_buckets_ms[bucket_name]}')

    lines.append("# HELP vtt_socket_events_total Total observed socket events.")
    lines.append("# TYPE vtt_socket_events_total counter")
    lines.append(f"vtt_socket_events_total {socket_total}")
    lines.append("# HELP vtt_socket_events_by_name_total Observed socket events by event name.")
    lines.append("# TYPE vtt_socket_events_by_name_total counter")
    for event_name in sorted(socket_by_name.keys()):
        safe_name = str(event_name).replace('"', '\\"')
        lines.append(f'vtt_socket_events_by_name_total{{event="{safe_name}"}} {socket_by_name[event_name]}')
    lines.append("# HELP vtt_socket_conflicts_total Total emitted realtime state conflicts.")
    lines.append("# TYPE vtt_socket_conflicts_total counter")
    lines.append(f"vtt_socket_conflicts_total {socket_conflicts_total}")
    lines.append("# HELP vtt_socket_resync_requests_total Total snapshot resync requests.")
    lines.append("# TYPE vtt_socket_resync_requests_total counter")
    lines.append(f"vtt_socket_resync_requests_total {socket_resync_requests_total}")
    lines.append("# HELP vtt_socket_reconnect_recoveries_total Total successful session join recoveries.")
    lines.append("# TYPE vtt_socket_reconnect_recoveries_total counter")
    lines.append(f"vtt_socket_reconnect_recoveries_total {socket_reconnect_recoveries_total}")

    lines.append("# HELP vtt_play_transitions_total Total play session transitions.")
    lines.append("# TYPE vtt_play_transitions_total counter")
    lines.append(f"vtt_play_transitions_total {play_total}")
    lines.append("# HELP vtt_play_transitions_by_target_total Play transitions grouped by target status.")
    lines.append("# TYPE vtt_play_transitions_by_target_total counter")
    for target in sorted(play_by_target.keys()):
        safe_target = str(target).replace('"', '\\"')
        lines.append(f'vtt_play_transitions_by_target_total{{target="{safe_target}"}} {play_by_target[target]}')

    body = "\n".join(lines) + "\n"
    return Response(body, mimetype="text/plain; version=0.0.4")
