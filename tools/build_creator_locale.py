#!/usr/bin/env python3
"""Compile reviewed, source-pinned presentation names; never derive character mechanics."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'vtt/rules_content'
PIN_DIR = ROOT / 'tools/creator_locale'
OUTPUT = CONTENT / 'srd-5.2.1-en/generated/creator-display.json'
CORE = {'class': 12, 'subclass': 12, 'class-feature': 232, 'class-option': 38,
        'species': 9, 'background': 4, 'feat': 17, 'spell': 339,
        'armor': 13, 'weapon': 38, 'tool': 25, 'gear': 108}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {'ruleId', 'type'}:
                yield from strings(item)


def compile_display(root=ROOT):
    content = root / 'vtt/rules_content'
    pin_dir = root / 'tools/creator_locale'
    pins = read(pin_dir / 'pins.json')
    terms = read(pin_dir / 'terms.json')
    if pins['review']['status'] != 'approved_identity_pairs':
        raise ValueError('Identity review is required')
    required={f'vtt/rules_content/srd-5.2.1-{loc}/generated/compendium.json' for loc in ['de','en']} | {'vtt/rules_content/srd-5.2.1-de/generated/creator-data.json'}
    if not required <= pins['sourceHashes'].keys():
        raise ValueError('Canonical data and both compendia must be pinned')
    for name, expected in pins['sourceHashes'].items():
        path = Path(name)
        if not name.startswith('vtt/rules_content/') or '..' in path.parts or digest(root / path) != expected:
            raise ValueError(f'Reviewed source changed: {name}')
    entities = {locale: {entry['id']: entry for entry in read(content / f'srd-5.2.1-{locale}/generated/compendium.json')['entities']}
                for locale in ('de', 'en')}
    canonical = read(content / 'srd-5.2.1-de/generated/creator-data.json')
    sources = pins['sourceHashes']
    model_ids={entry['id'] for collection in ['classes','species','backgrounds','feats','classOptions'] for entry in canonical[collection]}
    model_ids.update(canonical['spells'])
    model_ids.update(entry['id'] for kind in ['items', 'weapons', 'armor']
                     for entry in canonical['equipment'][kind])
    for cls in canonical['classes']:
        for row in cls['levels']:
            model_ids.update(feature['id'] for feature in row['features'] if feature.get('id'))
        for subclass_id in cls['subclasses']:
            subclass=entities['de'][subclass_id]
            if subclass['type']!='subclass' or subclass['documentId']!=cls['id'].rsplit('.',1)[0]:
                raise ValueError('Invalid canonical subclass reference')
            model_ids.add(subclass_id)
            model_ids.update(subclass['features'])
    if not model_ids <= pins['entities'].keys():
        raise ValueError('Missing canonical model names')
    # Three genuine core feature headings are reading-only: progression labels use
    # count-suffixed names with no entity ID. Validate their canonical class/document anchors.
    class_documents={cls['id'].rsplit('.',1)[0] for cls in canonical['classes']}
    for canonical_id in pins['entities'].keys()-model_ids:
        entry=entities['de'][canonical_id]
        if entry['type']!='class-feature' or entry['documentId'] not in class_documents:
            raise ValueError('Identity not referenced by the canonical creator model')
        document=read(content / f'srd-5.2.1-de/documents/{entry["documentId"]}.json')
        if entry['url'].split('#',1)[-1] not in {block['ruleId'] for block in document['blocks']}:
            raise ValueError('Reading-only feature lacks a canonical source anchor')
    def source_term(pin, field='name'):
        path = f'vtt/rules_content/srd-5.2.1-en/documents/{pin["documentId"]}.json'
        if path not in sources:
            raise ValueError('Term source must be pinned')
        block = next(block for block in read(root / path)['blocks'] if block['ruleId'] == pin['ruleId'])
        value = pin[field]
        if pin['quote'] != value or not any(re.search(r'(?<!\w)'+re.escape(value)+r'(?!\w)',text) for text in strings(block)):
            raise ValueError(f'Term not found verbatim in its source: {value}')
        return value

    names, seen, counts = {}, set(), Counter()
    for canonical_id, pin in sorted(pins['entities'].items()):
        de = entities['de'][canonical_id]
        en = entities['en'][pin['enEntityId']]
        if de['type'] != en['type'] or en['id'] in seen:
            raise ValueError(f'Non-bijective or mismatched identity: {canonical_id}')
        for locale, entry in [('de', de), ('en', en)]:
            path = f'vtt/rules_content/srd-5.2.1-{locale}/documents/{entry["documentId"]}.json'
            if path not in sources:
                raise ValueError(f'Unreviewed source document: {canonical_id}')
        seen.add(en['id'])
        counts[de['type']] += 1
        names[canonical_id] = {'name': en['name'], 'enEntityId': en['id'],
                               'documentId': en['documentId'], 'url': en['url']}
        if pin.get('displayNameSource'):
            ref = pin['displayNameSource']
            if (de['type'] not in {'armor', 'weapon', 'tool', 'gear'} or
                    ref['documentId'] != en['documentId'] or
                    ref['ruleId'] != en['url'].split('#', 1)[-1]):
                raise ValueError('Display name source must match the equipment entity anchor')
            names[canonical_id]['name'] = source_term(ref)
            names[canonical_id]['displayNameSource'] = dict(ref)
        if de['type']=='subclass':
            document=read(content / f'srd-5.2.1-en/documents/{en["documentId"]}.json')
            order={block['ruleId']:index for index,block in enumerate(document['blocks'])}
            features=[entry for entry in entities['en'].values() if entry['type']=='class-feature' and entry['documentId']==en['documentId'] and entry.get('subclass')==en['name']]
            expected_features={pins['entities'][feature_id]['enEntityId'] for feature_id in de['features']}
            if not features or {entry['id'] for entry in features}!=expected_features:
                raise ValueError('Subclass feature index is incomplete')
            features.sort(key=lambda entry:order[entry.get('anchor') or entry['url'].split('#',1)[1]])
            names[canonical_id]['featureIds']=[entry['id'] for entry in features]
        if pin.get('sourceDifferences'):
            if set(pin['sourceDifferences'])-{'components'}:
                raise ValueError('Source difference needs an explicit UI contract')
            # Genuine edition differences are disclosed, never applied to the canonical engine.
            names[canonical_id]['sourceDifferences'] = pin['sourceDifferences']
    if dict(counts) != CORE:
        raise ValueError(f'Incomplete bounded identity coverage: {dict(counts)}')
    for kind in CORE:
        if {entry['id'] for entry in entities['en'].values() if entry['type'] == kind} != {
                pin['enEntityId'] for key, pin in pins['entities'].items() if entities['de'][key]['type'] == kind}:
            raise ValueError(f'English identity coverage differs: {kind}')

    term_ids = {kind: {entry['id'] for entry in canonical[kind]}
                for kind in ['abilities', 'skills', 'languages', 'alignments']}
    term_ids.update({
        'weaponMasteries': {entry['mastery'] for entry in canonical['equipment']['weapons']},
        'weaponProperties': {prop['name'] for entry in canonical['equipment']['weapons'] for prop in entry['properties']},
        'coins': set(canonical['equipment']['coins']),
    })
    labels = {}
    for key, pin in sorted(terms['terms'].items()):
        kind, canonical_id = key.split(':', 1)
        if kind not in term_ids:
            raise ValueError('Unsupported creator term kind')
        if canonical_id not in term_ids[kind]:
            raise ValueError(f'Unknown canonical term: {key}')
        if kind == 'coins' and not pin.get('abbreviation'):
            raise ValueError('Coin display needs a source-backed abbreviation')
        labels[key] = {'name': source_term(pin), 'documentId': pin['documentId'], 'ruleId': pin['ruleId']}
        if pin.get('abbreviation'):
            labels[key]['abbreviation'] = source_term(pin['abbreviation'], 'value')
    for kind, expected_ids in term_ids.items():
        if {key.split(':', 1)[1] for key in labels if key.startswith(kind + ':')} != expected_ids:
            raise ValueError(f'Incomplete term coverage: {kind}')
    return {'schemaVersion': 1, 'locale': 'en',
            'canonicalHash': digest(content / 'srd-5.2.1-de/generated/creator-data.json'),
            'sourceHashes': sources, 'names': names, 'terms': labels,
            'coverage': {kind: {'total': count, 'mapped': counts[kind]} for kind, count in CORE.items()},
            'unresolved': ['species-subchoices', 'remaining-rule-labels', 'validation', 'editor']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    payload = json.dumps(compile_display(), ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != payload:
            raise SystemExit('Stale creator display data; review sources and regenerate')
    else:
        OUTPUT.write_text(payload, encoding='utf-8')
    print('847 reviewed entity names, 74 source-backed terms; pinned sources verified')


if __name__ == '__main__':
    main()
