#!/usr/bin/env python3
"""Seal an `original` Regelwerk package after its documents were written.

Recomputes every document digest, rewrites the manifest's document list in
reading order, pins the attribution file and the clean-room hand-off digest in
source-locks.json, then validates the package and regenerates its reader
artifacts. Coverage (card ranges and sections) stays as declared in the
manifest; review ranges are changed by hand after owner sign-off.

    python3 tools/seal_original_package.py vtt/rules_content/<rulesetId> --handoff-sha256 <hex>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from vtt.rules_content.generator import write_artifacts  # noqa: E402
from vtt.rules_content.validator import SOURCE_LOCKS_PATH, document_digest, validate_package  # noqa: E402


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("package", type=Path)
    parser.add_argument("--handoff-sha256", required=True, help="sha256 of the sealed clean-room hand-off bundle")
    args = parser.parse_args()
    package = args.package.resolve()
    manifest = _read(package / "manifest.json")
    if manifest.get("kind") != "original":
        parser.exit(1, "only original packages are sealed with this tool\n")

    documents = []
    for path in sorted((package / "documents").glob("*.json")):
        document = _read(path)
        document["digest"] = document_digest(document)
        _write(path, document)
        documents.append(document)
    documents.sort(key=lambda item: (item["order"], item["documentId"]))
    manifest["documents"] = [
        {"documentId": item["documentId"], "slug": item["slug"], "title": item["title"], "digest": item["digest"]}
        for item in documents
    ]

    attribution_sha256 = hashlib.sha256((package / manifest["license"]["attributionFile"]).read_bytes()).hexdigest()
    manifest["license"]["attributionSha256"] = attribution_sha256
    manifest["source"]["sha256"] = args.handoff_sha256
    _write(package / "manifest.json", manifest)

    locks = _read(SOURCE_LOCKS_PATH)
    entry = {
        "rulesetId": manifest["rulesetId"],
        "sourceTitle": manifest["source"]["title"],
        "sourcePublicationDate": manifest["source"]["publicationDate"],
        "retrievedAt": manifest["source"]["retrievedAt"],
        "sourceUrl": manifest["source"]["url"],
        "sourceSha256": args.handoff_sha256,
        "sourcePageCount": manifest["source"]["pageCount"],
        "licenseId": manifest["license"]["id"],
        "licenseUrl": manifest["license"]["url"],
        "attributionFile": manifest["license"]["attributionFile"],
        "attributionSha256": attribution_sha256,
    }
    locks["sources"] = [source for source in locks["sources"] if source["rulesetId"] != manifest["rulesetId"]] + [entry]
    _write(SOURCE_LOCKS_PATH, locks)

    report = validate_package(package)
    for path in write_artifacts(package):
        print(path)
    print(json.dumps(report.to_wire(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
