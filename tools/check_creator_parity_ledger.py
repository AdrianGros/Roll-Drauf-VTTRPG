"""Validate the C0 creator parity ledger against the approved milestone plan.

Run from any directory with ``python3 tools/check_creator_parity_ledger.py``.
Uses only the Python standard library and never touches application data.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/creator-parity-ledger-v1.csv"
PLAN = ROOT / "docs/decisions/CHARACTER_CREATOR_PARITY_PROGRAM_V1.md"
FIELDS = (
    "id", "capability", "status", "severity", "acceptance_owner",
    "area_owner", "criterion", "evidence_refs", "next_milestone", "finding",
)
STATUSES = {"accepted", "partial", "open", "inapplicable"}
SEVERITIES = {"info", "low", "medium", "high", "critical"}
AREAS = {"Creator UX", "Rules", "Sheet/VTT", "Character lifecycle", "Content/CE"}


def planned_owners() -> dict[int, set[str]]:
    """Read each C1-C10 matrix trace so the ledger cannot silently drift."""
    owners: dict[int, set[str]] = defaultdict(set)
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"C(?:[1-9]|10)", cells[0]):
            continue
        milestone = cells[0]
        for start, end in re.findall(r"(\d+)(?:\s*[–-]\s*(\d+))?", cells[4]):
            first = int(start)
            last = int(end) if end else first
            if first > last:
                raise ValueError(f"{milestone}: reversed matrix range {first}-{last}")
            for item_id in range(first, last + 1):
                owners[item_id].add(milestone)
    return owners


def validate() -> list[str]:
    errors: list[str] = []
    owners = planned_owners()
    with LEDGER.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != FIELDS:
            return [f"CSV headers must be {', '.join(FIELDS)}"]
        rows = list(reader)

    ids: list[int] = []
    for number, row in enumerate(rows, start=2):
        label = f"line {number}"
        if None in row or any(value is None for value in row.values()):
            errors.append(f"{label}: malformed CSV column count")
            continue
        for field in FIELDS:
            if not row[field].strip():
                errors.append(f"{label}: {field} is empty")
        try:
            item_id = int(row["id"])
            ids.append(item_id)
        except ValueError:
            errors.append(f"{label}: id is not an integer")
            continue
        if row["status"] not in STATUSES:
            errors.append(f"{label}: invalid status {row['status']!r}")
        if row["severity"] not in SEVERITIES:
            errors.append(f"{label}: invalid severity {row['severity']!r}")
        if row["acceptance_owner"] != "Roll Drauf product owner":
            errors.append(f"{label}: unexpected acceptance owner")
        if row["area_owner"] not in AREAS:
            errors.append(f"{label}: invalid area owner {row['area_owner']!r}")
        if row["next_milestone"] not in owners.get(item_id, set()):
            errors.append(f"{label}: {row['next_milestone']} does not own item {item_id} in plan v1")

        refs = row["evidence_refs"].split(";")
        for ref in refs:
            path_text, separator, node = ref.partition("::")
            path = (ROOT / path_text).resolve()
            if path == ROOT or ROOT not in path.parents or not path.is_file():
                errors.append(f"{label}: missing or external evidence path {path_text!r}")
                continue
            if separator and (path.suffix != ".py" or f"def {node}(" not in path.read_text(encoding="utf-8")):
                errors.append(f"{label}: missing pytest node {ref!r}")
        if row["status"] == "accepted" and not any(
            ref.startswith("docs/proofs/") or (ref.startswith("tests/") and "::" in ref)
            for ref in refs
        ):
            errors.append(f"{label}: accepted item needs direct test or proof")
        if row["status"] == "inapplicable" and "owner-approved" not in row["finding"].lower():
            errors.append(f"{label}: inapplicable item needs owner-approved exception in finding")

    counts = Counter(ids)
    if set(ids) != set(range(1, 49)) or len(ids) != 48:
        errors.append(f"expected exactly IDs 1-48; missing={sorted(set(range(1, 49)) - set(ids))}; duplicates={sorted(k for k, v in counts.items() if v > 1)}")
    if set(owners) != set(range(1, 49)):
        errors.append("plan v1 does not map every matrix point in C1-C10")
    if not errors:
        statuses = Counter(row["status"] for row in rows)
        print(f"Creator parity ledger valid: 48/48 rows; statuses {dict(sorted(statuses.items()))}")
    return errors


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(f"ERROR: {problem}", file=sys.stderr)
    raise SystemExit(1 if problems else 0)
