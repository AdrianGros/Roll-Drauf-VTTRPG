"""The whole run in one command: preflight -> views -> flows -> evidence.

    python -m tools.robots.run_all [--out DIR]

  * preflight FIRST — a broken harness produces `blocked`, never fake
    findings (see stack.py/preflight.py's own reasoning).
  * every suite runs as a subprocess so one crashing suite cannot take
    the others down with it; exit codes are the status contract: 0
    passed, 1 failed (real findings), 2 blocked (infrastructure).
  * one run directory, one run.json, one report.md (report.py).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from tools.robots.report import REPO, RunEvidence, SuiteRecord

PY = str(REPO / "venv" / "bin" / "python")


def _run_suite(ev: RunEvidence, name: str, argv: list[str]) -> SuiteRecord:
    out_dir = ev.suite_dir(name)
    record = SuiteRecord(name=name)
    log_path = out_dir / "log.txt"
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            argv, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    record.exit_code = completed.returncode
    record.status = {0: "passed", 1: "failed", 2: "blocked"}.get(
        completed.returncode, "inconclusive")
    record.seconds = round(time.monotonic() - started, 1)
    record.detail_path = str(log_path.relative_to(ev.run_dir))

    findings_json = out_dir / f"{name}.json"
    for candidate in (out_dir / f"{name}.json",
                     ev.run_dir.parent / f"vtt-{name.replace('_', '-')}.json"):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data.get("findings"), list):
                    record.findings = len(data["findings"])
                elif isinstance(data.get("flows"), dict):
                    record.findings = sum(len(v) for v in data["flows"].values())
            except Exception:
                pass
            break
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.run_all")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    run_dir = args.out or (REPO / "artifacts" / "robots" /
                           time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime()))
    run_dir.mkdir(parents=True, exist_ok=True)
    ev = RunEvidence(run_dir=run_dir)

    print(f"Preflight …")
    from tools.robots.preflight import run_preflight
    preflight_dir = ev.suite_dir("preflight")
    started = time.monotonic()
    preflight_result = run_preflight(preflight_dir)
    preflight_record = SuiteRecord(
        name="preflight", status=preflight_result["status"],
        exit_code=0 if preflight_result["status"] == "passed" else 2,
        seconds=round(time.monotonic() - started, 1),
        detail_path=str((preflight_dir / "preflight.json").relative_to(run_dir)))
    ev.suites.append(preflight_record)
    print(f"  {preflight_record.status}")

    if preflight_record.status != "passed":
        ev.write()
        print(f"\nBLOCKED at preflight — no suite runs against a broken harness.")
        print(f"Report: {run_dir / 'report.md'}")
        return 2

    for name, module in (("views", "tools.robots.views"),
                         ("flows", "tools.robots.flows")):
        print(f"{name} …")
        record = _run_suite(
            ev, name, [PY, "-m", module, "--out", str(ev.suite_dir(name) / f"{name}.json")])
        ev.suites.append(record)
        print(f"  {record.status} ({record.findings} finding(s), {record.seconds}s)")

    ev.write()
    overall = "passed" if all(s.status == "passed" for s in ev.suites) else (
        "blocked" if any(s.status == "blocked" for s in ev.suites) else "failed")
    print(f"\nOverall: {overall}")
    print(f"Report: {run_dir / 'report.md'}")
    return {"passed": 0, "blocked": 2}.get(overall, 1)


if __name__ == "__main__":
    sys.exit(main())
