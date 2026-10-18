"""Source-package model of the SRD character creator (pure, no Flask).

Every creator state and every finished character pins the content packages it was
built from, so a later package version can never silently change a character.
Only the published SRD package is registered today; further package kinds
(homebrew, licensed packs) plug in here once they exist.
"""

from __future__ import annotations

SRD_SOURCE_ID = "srd-5.2.1-de"
SOURCE_KINDS = ("srd", "homebrew", "licensed")

_REGISTRY = {
    SRD_SOURCE_ID: {
        "id": SRD_SOURCE_ID,
        "kind": "srd",
        "title": "Roll Drauf Regelwerk — SRD 5.2.1 (Deutsch)",
        "license": "CC-BY-4.0",
        "licenseUrl": "https://creativecommons.org/licenses/by/4.0/legalcode.de",
    }
}


def registered_sources() -> list[dict]:
    return [dict(entry) for entry in _REGISTRY.values()]


def default_source_ids() -> list[str]:
    return [SRD_SOURCE_ID]


def pin_sources(data: dict, source_ids=None) -> list[dict]:
    """Pins (id, kind, version, license, digest) for the enabled sources."""
    pins = []
    for source_id in source_ids or default_source_ids():
        entry = _REGISTRY[source_id]
        if source_id == data["rulesetId"]:
            pins.append({**entry, "version": data["rulesetVersion"], "digest": data["packageDigest"]})
    return pins


def validate_source_ids(source_ids) -> list[str]:
    """Problems with a requested source list (empty list means fine)."""
    if source_ids is None:
        return []
    if not isinstance(source_ids, list) or not source_ids:
        return ["Die Quellenliste muss mindestens eine Quelle enthalten."]
    problems = []
    seen = set()
    for source_id in source_ids:
        if not isinstance(source_id, str) or source_id not in _REGISTRY:
            problems.append(f"Unbekannte oder nicht freigeschaltete Quelle: {str(source_id)[:60]}")
        elif source_id in seen:
            problems.append(f"Quelle doppelt angegeben: {source_id}")
        seen.add(source_id if isinstance(source_id, str) else repr(source_id))
    if SRD_SOURCE_ID not in seen:
        problems.append("Die SRD-Quelle ist Pflicht.")
    return problems


def pin_status(data: dict, pins) -> str:
    """'current' when every pin matches the loaded package, otherwise 'drifted'."""
    if not isinstance(pins, list) or not pins:
        return "drifted"
    for pin in pins:
        if not isinstance(pin, dict):
            return "drifted"
        if pin.get("id") == data["rulesetId"] and (
            pin.get("version") != data["rulesetVersion"] or pin.get("digest") != data["packageDigest"]
        ):
            return "drifted"
    return "current"
