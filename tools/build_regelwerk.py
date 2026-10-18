#!/usr/bin/env python3
"""Build or verify deterministic Regelwerk reader artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from vtt.rules_content.generator import DEFAULT_PACKAGE, stale_artifacts, write_artifacts  # noqa: E402
from vtt.rules_content.validator import PackageValidationError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--check", action="store_true", help="fail if checked-in output is stale")
    args = parser.parse_args()
    try:
        if args.check:
            stale = stale_artifacts(args.package)
            if stale:
                parser.exit(1, f"Regelwerk generated artifacts are stale: {', '.join(stale)}\n")
            print("Regelwerk generated artifacts are current.")
            return 0
        for path in write_artifacts(args.package):
            print(path)
        return 0
    except (PackageValidationError, OSError, ValueError) as exc:
        parser.exit(1, f"Regelwerk generation failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
