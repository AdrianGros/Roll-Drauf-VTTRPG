"""Read-only presentation overlay. Canonical creator data and mechanics stay untouched."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from .validator import CONTENT_ROOT

DISPLAY_FILE = CONTENT_ROOT / 'srd-5.2.1-en/generated/creator-display.json'
CANONICAL_FILE = CONTENT_ROOT / 'srd-5.2.1-de/generated/creator-data.json'


class DisplayUnavailable(ValueError):
    pass


@lru_cache(maxsize=1)
def canonical_data_hash():
    return hashlib.sha256(CANONICAL_FILE.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def load_creator_display():
    try:
        payload = json.loads(DISPLAY_FILE.read_text(encoding='utf-8'))
        if payload['schemaVersion'] != 1 or payload['locale'] != 'en' or payload['canonicalHash'] != canonical_data_hash():
            raise DisplayUnavailable('Creator display version mismatch')
        required={f'vtt/rules_content/srd-5.2.1-{loc}/generated/compendium.json' for loc in ['de','en']} | {'vtt/rules_content/srd-5.2.1-de/generated/creator-data.json'}
        if not required <= payload['sourceHashes'].keys():
            raise DisplayUnavailable('Missing display source pins')
        for name, expected in payload['sourceHashes'].items():
            path = Path(name)
            if not name.startswith('vtt/rules_content/') or '..' in path.parts:
                raise DisplayUnavailable('Invalid display source')
            source = CONTENT_ROOT.joinpath(*path.parts[2:])
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise DisplayUnavailable('Creator display source changed')
        return payload
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise DisplayUnavailable('Creator display data unavailable') from error


def display_etag(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
