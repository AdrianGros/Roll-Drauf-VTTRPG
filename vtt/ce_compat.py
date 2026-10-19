"""Former Creation Engine G1 runtime bridge, kept as an inert seam.

The G1 kernel (runtime representations of characters and tokens, pinned homebrew race origins) is archived
under archive/creation-engine-g1/. Production never held a representation or a race origin (2026-10-19:
ce_representations = 0, ce_character_origins = 0), so every caller already took its legacy path; these
functions now always do. Callers keep this interface so a future runtime can plug back in here.
"""


def adapter():
    return None


def character_projection(character, *, operation="read"):
    return None


def token_reference(token):
    return None


def homebrew_origin(character):
    return None
