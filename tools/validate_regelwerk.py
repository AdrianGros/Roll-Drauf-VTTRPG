#!/usr/bin/env python3
"""Validate a Regelwerk package and print its deterministic coverage report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DEFAULT_PACKAGE = Path(__file__).resolve().parents[1] / "vtt" / "rules_content" / "srd-5.2.1-de"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from vtt.rules_content import PackageValidationError, validate_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--expect-digest", help="fail unless the package has this sha256: digest")
    args = parser.parse_args()
    try:
        report = validate_package(args.package, expected_digest=args.expect_digest)
    except PackageValidationError as exc:
        parser.exit(1, f"Regelwerk validation failed: {exc}\n")
    print(json.dumps(report.to_wire(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
