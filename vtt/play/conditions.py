"""S05: the canonical token-condition catalog.

Apply decision (docs/PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md): a fixed
D&D 5e core list of 15 conditions ships now; a user-defined/custom catalog
is deferred to a later admin-tooling slice. Conditions stay stored as
``token.metadata_json.conditions`` (the existing location, per the Apply
decision to avoid a migration) but each entry must now be one of these ids
-- previously any free-form string was accepted with no validation at all.

This module is deliberately just data + one validation helper: it is safe
to import from both vtt/socket_handlers.py (server-side enforcement) and
any future admin/catalog surface, without depending on anything else.
"""

CONDITION_CATALOG = [
    {"id": "blinded", "label": "Blind"},
    {"id": "charmed", "label": "Bezaubert"},
    {"id": "concentrating", "label": "Konzentriert"},
    {"id": "deafened", "label": "Taub"},
    {"id": "exhausted", "label": "Erschöpft"},
    {"id": "frightened", "label": "Verängstigt"},
    {"id": "grappled", "label": "Gepackt"},
    {"id": "incapacitated", "label": "Kampfunfähig"},
    {"id": "invisible", "label": "Unsichtbar"},
    {"id": "paralyzed", "label": "Gelähmt"},
    {"id": "petrified", "label": "Versteinert"},
    {"id": "poisoned", "label": "Vergiftet"},
    {"id": "prone", "label": "Liegend"},
    {"id": "restrained", "label": "Festgesetzt"},
    {"id": "stunned", "label": "Betäubt"},
    {"id": "unconscious", "label": "Bewusstlos"},
]

CONDITION_IDS = frozenset(entry["id"] for entry in CONDITION_CATALOG)


def validate_condition_ids(raw_conditions):
    """Return (list_of_valid_ids, error) for a metadata_json.conditions value.

    Deliberately permissive about ordering/duplicates (de-duplicates,
    preserves first-seen order) but strict about the value set -- an
    unknown id is a hard rejection, not a silent drop, so a typo'd or
    stale client value surfaces immediately instead of quietly vanishing.
    """
    if raw_conditions is None:
        return [], None
    if not isinstance(raw_conditions, list):
        return None, {"code": "bad_request", "message": "conditions must be a list"}

    seen = []
    for entry in raw_conditions:
        condition_id = str(entry).strip().lower()
        if condition_id not in CONDITION_IDS:
            return None, {"code": "bad_request", "message": f"unknown condition: {condition_id}"}
        if condition_id not in seen:
            seen.append(condition_id)
    return seen, None
