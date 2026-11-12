"""One existing-character writer boundary; caller authorizes and commits the transaction."""
from vtt.extensions import db
from vtt.models import Character


def lock_character(character_id):
    # Even when a permission/context read populated the identity map before the
    # lock, dependent mutations must start from the newly locked database row.
    return db.session.get(Character, character_id, with_for_update=True, populate_existing=True)
