"""Stil-Ratchet (Robot R4): design-token and language debt may only
shrink, never grow (Designbrief §7 Mess-Gates, Regelwerk §4).

Betterer-style ratchet (ROBOT_FLEET_AND_RULEBOOK §8.4): the baseline
file stil_baseline.json records the current violation count PER FILE.
A run fails when any file's count rises or a new offending file appears;
when counts drop, the baseline is lowered automatically and must be
committed with the improvement.  Per-file ratcheting stops one file's
cleanup from masking another file's new debt.

Checks:
  * hex-literals  — #rgb/#rrggbb outside theme.css (the token catalog);
                    vendored/minified assets are excluded, they are not
                    ours to lint.
  * umlaut-ersatz — oe/ue-Ersatzschreibungen (oeffnen|zurueck|wuerfel|
                    loeschen) in templates; echte Umlaute sind Pflicht.

No Node toolchain exists in this repo, so this is a Python ratchet; if a
package.json ever appears, replace the hex check with
stylelint-declaration-strict-value and keep only the ratchet logic here.

Exit codes: 0 = ok (baseline may have been lowered), 1 = debt grew.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from tools.robots.report import REPO

BASELINE_PATH = Path(__file__).resolve().parent / "stil_baseline.json"

VENDORED = {"gsap.min.js", "socket.io.min.js"}
TOKEN_CATALOG = {"theme.css"}

CHECKS = {
    "hex-literals": {
        "pattern": re.compile(r"#[0-9a-fA-F]{3}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b"),
        "roots": ["vtt/templates", "vtt/static/css", "vtt/static/js"],
        "suffixes": {".html", ".css", ".js"},
    },
    # Design-Jury 2026-08-25: "PRIMAERE GILDE"/"prueft"/"ausschliesslich"
    # standen im RENDERING neben korrekten Umlauten — die Strings kommen
    # aus JS/Python-Content, die der reine Template-Grep nie sah.  Daher
    # Muster erweitert und JS + content_defaults in den Scan genommen.
    "umlaut-ersatz": {
        "pattern": re.compile(
            r"(?i)\b(oeffnen|zurueck|wuerfel|loeschen|prueft|pruefen"
            r"|primaer\w*|ausschliess\w*|veraender\w*|waehl\w*|uebersicht"
            r"|naechste\w*|gewaehlt\w*)"),
        "roots": ["vtt/templates", "vtt/static/js", "vtt/content_defaults.py"],
        "suffixes": {".html", ".js", ".py"},
    },
}


def _scan() -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    for check_name, check in CHECKS.items():
        per_file: dict[str, int] = {}
        for root in check["roots"]:
            root_path = REPO / root
            paths = ([root_path] if root_path.is_file()
                     else sorted(root_path.rglob("*")))
            for path in paths:
                if (path.suffix not in check["suffixes"]
                        or path.name in VENDORED
                        or path.name in TOKEN_CATALOG):
                    continue
                count = len(check["pattern"].findall(
                    path.read_text(encoding="utf-8", errors="replace")))
                if count:
                    per_file[str(path.relative_to(REPO))] = count
        results[check_name] = per_file
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.stil_lint")
    parser.add_argument("--init", action="store_true",
                        help="Baseline aus dem Ist-Zustand neu schreiben")
    parser.add_argument("--check-only", action="store_true",
                        help="Baseline bei Verbesserung NICHT absenken")
    args = parser.parse_args(argv)

    current = _scan()

    if args.init or not BASELINE_PATH.exists():
        BASELINE_PATH.write_text(
            json.dumps(current, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8")
        totals = {name: sum(files.values()) for name, files in current.items()}
        print(f"stil_lint: Baseline geschrieben — {totals} "
              f"({BASELINE_PATH.relative_to(REPO)}; bitte committen)")
        return 0

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    grew: list[str] = []
    improved = False
    for check_name, per_file in current.items():
        base_files = baseline.get(check_name, {})
        for file_name, count in per_file.items():
            allowed = base_files.get(file_name, 0)
            if count > allowed:
                grew.append(f"{check_name}: {file_name} {allowed} → {count}")
        for file_name, allowed in base_files.items():
            if per_file.get(file_name, 0) < allowed:
                improved = True

    totals = {name: sum(files.values()) for name, files in current.items()}
    if grew:
        print("stil_lint: SCHULD GEWACHSEN (Regelwerk §4 — Zahl darf nur sinken):")
        for line in grew:
            print(f"  {line}")
        print(f"  aktuell gesamt: {totals}")
        return 1

    if improved and not args.check_only:
        BASELINE_PATH.write_text(
            json.dumps(current, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8")
        print(f"stil_lint: ok, Schuld gesunken — Baseline abgesenkt auf "
              f"{totals} (bitte committen)")
    else:
        print(f"stil_lint: ok — {totals}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
