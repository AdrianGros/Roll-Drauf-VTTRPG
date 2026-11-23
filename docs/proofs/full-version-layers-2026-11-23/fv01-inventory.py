"""Inspect candidate spell matches; deliberately approves no cross-language identity."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


root = Path(__file__).resolve().parents[3]
paths = {language: root / f"vtt/rules_content/srd-5.2.1-{language}/generated/compendium.json"
         for language in ["de", "en"]}
data = {language: json.loads(path.read_text())["entities"] for language, path in paths.items()}
classes = {language: {entry["name"]: entry.get("classKey", entry["documentId"].split(".")[-1])
                     for entry in entities if entry["type"] == "class"} for language, entities in data.items()}
schools = {"Bann": "Abjuration", "Beschwörung": "Conjuration", "Erkenntnis": "Divination",
           "Verzauberung": "Enchantment", "Hervorrufung": "Evocation", "Illusion": "Illusion",
           "Nekromantie": "Necromancy", "Verwandlung": "Transmutation"}


def signature(entry, language):
    school = schools[entry["school"]] if language == "de" else entry["school"]
    components = str(entry.get("components", "")).split("(")[0].replace("G", "S")
    return (entry["level"], school, bool(entry["ritual"]), bool(entry["concentration"]),
            "".join(sorted(set(re.findall("[VSM]", components)))),
            tuple(sorted(classes[language][name] for name in entry["classes"])))


english = defaultdict(list)
for entry in data["en"]:
    if entry["type"] == "spell":
        english[signature(entry, "en")].append(entry)
rows = []
for entry in data["de"]:
    if entry["type"] != "spell":
        continue
    candidates = english[signature(entry, "de")]
    rows.append({"canonical_id": entry["id"], "de_name": entry["name"],
                 "candidate_en_ids": [candidate["id"] for candidate in candidates],
                 "candidate_names": [candidate["name"] for candidate in candidates], "identity_approved": False})
report = {"status": "candidate_inventory_only_no_identity_assignments",
          "compendium_sha256": {language: hashlib.sha256(path.read_bytes()).hexdigest() for language, path in paths.items()},
          "spells": {"total": len(rows), "one_candidate": sum(len(row["candidate_en_ids"]) == 1 for row in rows),
                     "multiple_candidates": sum(len(row["candidate_en_ids"]) > 1 for row in rows),
                     "no_candidate": sum(not row["candidate_en_ids"] for row in rows)},
          "signature_limit": "Facet agreement is not semantic proof. Every selected pair requires comparison with the actual entries and a reviewed pin.",
          "candidate_rows": rows}
Path(__file__).with_name("fv01-spell-candidates.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "candidate_rows"}))
