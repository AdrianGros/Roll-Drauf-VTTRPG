"""Evidence bundle for one robot run: run.json + report.md, so every
run has a single identity (git SHA, timestamp, per-suite status) instead
of scattered JSON files nobody can correlate later.

Mirrors the sister suite's evidence.py in spirit, sized down to this
project's current three suites.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


@dataclass
class SuiteRecord:
    name: str
    status: str = "not_run"
    exit_code: int | None = None
    findings: int = 0
    seconds: float = 0.0
    detail_path: str = ""
    severity_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class RunEvidence:
    run_dir: Path
    git_sha: str = field(default_factory=_git_sha)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    suites: list[SuiteRecord] = field(default_factory=list)

    def suite_dir(self, name: str) -> Path:
        directory = self.run_dir / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write(self) -> None:
        run_json = {
            "git_sha": self.git_sha,
            "started_at": self.started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed" if all(
                s.status == "passed" for s in self.suites) else (
                "blocked" if any(s.status == "blocked" for s in self.suites)
                else "failed"),
            "suites": [vars(s) for s in self.suites],
        }
        (self.run_dir / "run.json").write_text(
            json.dumps(run_json, indent=2, ensure_ascii=False), encoding="utf-8")

        lines = [
            f"# Roll Drauf VTT — Robot Run {self.git_sha}",
            f"", f"Started: {self.started_at}", f"",
            "| Suite | Status | Findings | Seconds | Severity |",
            "|---|---|---:|---:|---|",
        ]
        for suite in self.suites:
            severity = ", ".join(
                f"{name}:{count}" for name, count in sorted(suite.severity_counts.items())
            ) or "-"
            lines.append(
                f"| {suite.name} | {suite.status} | {suite.findings} | "
                f"{suite.seconds:.1f} | {severity} |")
        lines.append("")
        lines.append(f"Overall: **{run_json['status']}**")
        (self.run_dir / "report.md").write_text(
            "\n".join(lines), encoding="utf-8")
