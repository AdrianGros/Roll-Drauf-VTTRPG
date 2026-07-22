"""Run a lightweight MVP launch rehearsal and write a consolidated report."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _run_step(name: str, command: list[str], workdir: Path):
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, cwd=workdir, capture_output=True, text=True)
    ended = datetime.now(timezone.utc)
    return {
        "name": name,
        "command": " ".join(command),
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = Path(os.getenv("MVP_REHEARSAL_OUT", f"ops/monitor/evidence/mvp_rehearsal_{timestamp}.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    python_bin = os.getenv("PYTHON_BIN") or sys.executable
    run_browser_smoke = os.getenv("RUN_BROWSER_SMOKE", "0").strip().lower() in {"1", "true", "yes", "on"}
    run_full_regression = os.getenv("RUN_FULL_REGRESSION", "0").strip().lower() in {"1", "true", "yes", "on"}

    steps = []
    steps.append(
        _run_step(
            "release_gate_evidence",
            [python_bin, "ops/monitor/release_gate_evidence.py"],
            repo_root,
        )
    )
    steps.append(
        _run_step(
            "targeted_regression",
            [python_bin, "-m", "pytest", "tests/test_ops_endpoints.py", "tests/test_play_rejoin_socket.py", "-q"],
            repo_root,
        )
    )

    if run_browser_smoke:
        steps.append(
            _run_step(
                "browser_smoke",
                [python_bin, "ops/monitor/browser_smoke.py"],
                repo_root,
            )
        )
    else:
        steps.append(
            {
                "name": "browser_smoke",
                "ok": True,
                "skipped": True,
                "reason": "set RUN_BROWSER_SMOKE=1 to enable",
            }
        )

    if run_full_regression:
        steps.append(
            _run_step(
                "full_regression",
                [python_bin, "-m", "pytest", "-q"],
                repo_root,
            )
        )
    else:
        steps.append(
            {
                "name": "full_regression",
                "ok": True,
                "skipped": True,
                "reason": "set RUN_FULL_REGRESSION=1 to enable",
            }
        )

    overall_ok = all(step.get("ok", False) for step in steps)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "overall_ok": overall_ok,
        "steps": steps,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[mvp-rehearsal] wrote {output_path}")
    print(f"[mvp-rehearsal] overall_ok={overall_ok}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())

