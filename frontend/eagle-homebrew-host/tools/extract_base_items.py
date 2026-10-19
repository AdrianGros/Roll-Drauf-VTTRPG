"""Builds the base-item index dnd5e's Trait.getBaseItem resolves (uuid -> name, type.value) from dnd5e pack sources."""
import json
import pathlib
import sys

import yaml

root, out = pathlib.Path(sys.argv[1]), sys.argv[2]
index = {}
for pack in ("equipment24", "items"):
    for path in sorted((root / "packs/_source" / pack).rglob("*.yml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or "_id" not in doc or doc.get("type") in (None, "folder"):
            continue
        system = doc.get("system") or {}
        index[f"Compendium.dnd5e.{pack}.Item.{doc['_id']}"] = {
            "name": doc.get("name"), "type": doc.get("type"),
            "system": {"type": {"value": (system.get("type") or {}).get("value")}}}
pathlib.Path(out).write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(index), "base items")
