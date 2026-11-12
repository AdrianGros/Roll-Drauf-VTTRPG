#!/usr/bin/env python3
"""Compile explicit, repository-authored UI messages; never inspect user documents."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def compile_catalog(check=False):
    inventory = json.loads((HERE / 'ui-inventory.json').read_text())
    index = json.loads((HERE / 'translation-index.json').read_text())
    translated = {}
    for path in sorted((HERE / 'translations').glob('en-*.json')):
        chunk = json.loads(path.read_text())
        if set(chunk) & set(translated):
            raise ValueError('Duplicate translation indices: ' + str(path))
        translated.update(chunk)
    if set(translated) != {str(i) for i in range(len(inventory))}:
        raise ValueError('Missing or extraneous English translation indices')
    overrides = json.loads((HERE / 'translations/de-overrides.json').read_text())
    messages = {}
    for i, row in enumerate(inventory):
        source = row['source']
        key = 'u_' + hashlib.sha1(source.encode()).hexdigest()[:12]
        if index[i] != key:
            raise ValueError('Source index changed at ' + str(i))
        en = translated[str(i)]
        de = overrides.get(str(i), source)
        placeholders = set(re.findall(r'\{[a-zA-Z0-9_]+\}', source))
        for value in (de, en):
            if set(re.findall(r'\{[a-zA-Z0-9_]+\}', value)) != placeholders:
                raise ValueError('Placeholder mismatch at ' + str(i))
        messages[key] = {'source': source, 'de': de, 'en': en}
    extra_overrides = []
    def reject_duplicate_sources(pairs):
        seen = set()
        for source, _row in pairs:
            if source in seen:
                raise ValueError('Duplicate extra source (a later entry would silently win): ' + source)
            seen.add(source)
        return dict(pairs)
    extra_rows = json.loads((HERE / 'extra-messages.json').read_text(), object_pairs_hook=reject_duplicate_sources)
    # Disjoint task files let workers add labels without sharing a mutable catalog.
    # Only the reviewed main extras may override an existing translation.
    for fragment in sorted((HERE / 'tasks').glob('*.json')):
        rows = json.loads(fragment.read_text(), object_pairs_hook=reject_duplicate_sources)
        if not isinstance(rows, dict):
            raise ValueError('Invalid task catalog: ' + fragment.name)
        for source, row in rows.items():
            existing = extra_rows.get(source)
            if existing is None:
                key = 'u_' + hashlib.sha1(source.encode()).hexdigest()[:12]
                previous = messages.get(key)
                if previous and previous.get('source') == source:
                    existing = {language: previous[language] for language in ('de', 'en')}
            if existing is not None and existing != row:
                raise ValueError('Conflicting task translation: ' + fragment.name + ': ' + source)
            extra_rows[source] = row
    for source, row in extra_rows.items():
        if not isinstance(source, str) or not source.strip() or not isinstance(row, dict):
            raise ValueError('Invalid extra message')
        if set(row) != {'de', 'en'}:
            raise ValueError('Incomplete extra message: ' + source)
        placeholders = set(re.findall(r'\{[a-zA-Z0-9_]+\}', source))
        for language in ('de', 'en'):
            value = row[language]
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Empty extra translation: ' + language + ': ' + source)
            if set(re.findall(r'\{[a-zA-Z0-9_]+\}', value)) != placeholders:
                raise ValueError('Extra placeholder mismatch: ' + language + ': ' + source)
        key = 'u_' + hashlib.sha1(source.encode()).hexdigest()[:12]
        if key in messages and messages[key]['source'] != source:
            raise ValueError('Extra source key collision: ' + source)
        previous = messages.get(key)
        if previous and any(previous[language] != row[language] for language in ('de', 'en')):
            # Same source, deliberately overridden: allowed, but never silent.
            extra_overrides.append((source, previous, row))
        messages[key] = {'source':source, **row}
    for source, previous, row in extra_overrides:
        print('NOTE extra-messages override differs from inventory translation: ' + json.dumps(source, ensure_ascii=False)
              + ' de ' + json.dumps(previous['de'], ensure_ascii=False) + ' -> ' + json.dumps(row['de'], ensure_ascii=False)
              + '; en ' + json.dumps(previous['en'], ensure_ascii=False) + ' -> ' + json.dumps(row['en'], ensure_ascii=False),
              file=sys.stderr)
    eagle = json.loads((HERE / 'eagle-sources.json').read_text())
    eagle_de = json.loads((HERE / 'translations/eagle-de.json').read_text())
    if set(eagle_de) != {str(i) for i in range(len(eagle))}:
        raise ValueError('Incomplete Eagle catalog')
    for i, row in enumerate(eagle):
        if set(re.findall(r'\{[^}]+\}',row['en'])) != set(re.findall(r'\{[^}]+\}',eagle_de[str(i)])):
            raise ValueError('Eagle placeholder mismatch: ' + row['key'])
        messages[row['key']] = {'de':eagle_de[str(i)],'en':row['en']}
    outputs = {ROOT / 'vtt/static/js/ui-catalog.js': '/* Generated by tools/i18n/build_catalog.py. */\nwindow.VTTUiMessages=' + json.dumps(messages,ensure_ascii=False,separators=(',',':')).replace('</','<\\/') + ';\n'}
    for language in ('de', 'en'):
        outputs[ROOT / f'vtt/static/i18n/ui.{language}.json'] = json.dumps({k:v[language] for k,v in messages.items()},ensure_ascii=False,indent=2) + '\n'
    for path, content in outputs.items():
        if check:
            if not path.exists() or path.read_text() != content:
                raise ValueError('Stale catalog: ' + str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
    print(f'{len(messages)} UI sources: DE/EN complete, placeholders and generated files verified')

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    compile_catalog(args.check)
