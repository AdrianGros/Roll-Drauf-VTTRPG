"""English native reader: complete source inventories, locale and mechanics isolation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from vtt import create_app
from vtt.rules_content import english
from tests.test_srd_sheet import site  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
API = '/api/rulesets/srd-5.2.1-en'


@pytest.fixture(scope='module')
def client():
    return create_app('testing').test_client()


def test_all_source_pages_and_source_inventories_are_present():
    coverage = english.coverage()
    assert coverage['complete'] is True
    assert coverage['missingPageRanges'] == []
    assert coverage['representedPageRanges'] == [{'first': 5, 'last': 364}]
    assert coverage['sourceLines']['unconsumed'] == 0
    assert coverage['entityCounts']['class-feature'] == 232
    assert coverage['entityCounts']['class-option'] == 38
    for check in ['statBlockIndex', 'classSpellLists']:
        assert coverage['checks'][check]['missing'] == []
        assert coverage['checks'][check]['expected'] == coverage['checks'][check]['found']
    counts = coverage['entityCounts']
    assert {key: counts[key] for key in ('spell', 'creature', 'magic-item', 'weapon', 'armor', 'tool')} == {
        'spell': 339, 'creature': 330, 'magic-item': 258, 'weapon': 38, 'armor': 13, 'tool': 25}
    report = json.loads((english.GENERATED / 'build-report.json').read_text())
    assert report['warnings'] == []


def test_source_provenance_distinguishes_authored_notes_from_rules():
    manifest = english.manifest()
    assert manifest['source']['pdfVerified'] is True
    assert hashlib.sha256((ROOT / 'vtt/static/regelwerk/SRD_CC_v5.2.1.pdf').read_bytes()).hexdigest() == manifest['source']['sha256']
    assert manifest['editorialPolicy']['officialBody'] == 'extracted'
    assert manifest['editorialPolicy']['paraphrased'] is False
    assert 'Creative Commons Attribution 4.0' in english.attribution()
    for item in manifest['documents']:
        document = english.document(item['documentId'])
        assert document['contentStatus'] == 'extracted'
        notes = [block for block in document['blocks'] if block['type'] == 'original-note']
        assert len(notes) == 1 and notes[0]['editorial'] is True
        assert notes[0]['text'].strip()


def test_every_catalogue_entity_has_a_readable_source_excerpt():
    entities = english.compendium()['entities']
    assert len({entity['id'] for entity in entities}) == len(entities)
    for entity in entities:
        assert entity['url'].startswith('/regelwerk/5.2.1/en/')
        resolved = english.entry(entity['id'])
        assert resolved is not None, entity['id']
        assert resolved[1], entity['id']
        assert not any(block.get('editorial') for block in resolved[1])
    spells = [entity for entity in entities if entity['type'] == 'spell']
    assert all(all(entity[key] for key in ('classes', 'castingTime', 'range', 'components', 'duration')) for entity in spells)
    assert {entity['level'] for entity in spells} == set(range(10))
    assert len({entity['school'] for entity in spells}) == 8


def test_public_native_routes_search_detail_filters_and_etags(client):
    assert client.get('/regelwerk/5.2.1/en').status_code == 200
    assert client.get('/regelwerk/5.2.1/en/license').status_code == 200
    assert client.get('/regelwerk/en').status_code == 200  # PDF reference remains
    response = client.get(API + '/manifest')
    navigation = response.get_json()
    assert navigation['rulesetId'] == english.RULESET_ID
    assert navigation['readerUrl'] == '/regelwerk/5.2.1/en'
    assert client.get(API + '/manifest', headers={'If-None-Match': response.headers['ETag']}).status_code == 304
    assert client.get('/api/rulesets/main?locale=en').get_json()['rulesetId'] == english.RULESET_ID
    assert client.get('/api/rulesets/main').get_json()['rulesetId'] == 'srd-5.2.1-de'
    listing = client.get('/api/rulesets').get_json()['rulesets']
    assert {book['rulesetId'] for book in listing} >= {'srd-5.2.1-en', 'srd-5.2.1-de'}
    response = client.get(API + '/compendium?type=spell&class=Wizard&level=3&school=Evocation&q=Fireball')
    result = response.get_json()
    assert result['total'] == 1
    fireball = result['items'][0]
    assert fireball['name'] == 'Fireball' and fireball['range'] == '150 feet'
    detail = client.get(API + '/compendium/entry/' + fireball['id']).get_json()
    assert '8d6' in json.dumps(detail['blocks'])
    assert client.get(fireball['url'].split('#')[0]).status_code == 200
    search = client.get(API + '/search?q=Fireball').get_json()['results']
    assert search and all(result['url'].startswith('/regelwerk/5.2.1/en/') for result in search)
    assert client.get(API + '/license').get_json()['editorialPolicy']['paraphrased'] is False


@pytest.mark.parametrize('query', ['type=unknown', 'level=10', 'limit=999', 'component=X', 'type=creature&cr_min=bad'])
def test_invalid_filter_requests_are_rejected(client, query):
    assert client.get(API + '/compendium?' + query).status_code == 400


def test_english_and_german_ids_and_pins_are_not_cross_resolved(client):
    english_fireball = client.get(API + '/compendium?type=spell&q=Fireball').get_json()['items'][0]
    german = client.get('/api/rulesets/srd-5.2.1-de/compendium?type=spell&q=Feuerball').get_json()['items'][0]
    assert english_fireball['id'] != german['id']
    assert client.get(API + '/compendium/entry/' + german['id']).status_code == 404
    assert client.get('/api/rulesets/srd-5.2.1-de/compendium/entry/' + english_fireball['id']).status_code == 404
    assert client.get(API + '/documents/../../manifest').status_code == 404
    assert client.get('/regelwerk/5.2.1/en/not-a-chapter').status_code == 404


@pytest.mark.parametrize('width', [1440, 390])
def test_english_preferences_reader_search_compendium_and_explicit_de_links(site, width):
    from playwright.sync_api import expect, sync_playwright
    app, origin, info = site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1', JSON.stringify({schema:1,language:'en',theme:'night'}));")
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(origin + '/regelwerk')
        expect(page.locator('#regelwerkArticle')).to_contain_text('Playing the Game')
        expect(page).to_have_url(origin + '/regelwerk/5.2.1/en')
        page.locator('#regelwerkSearchInput').fill('Fireball')
        page.locator('#regelwerkSearch button').click()
        expect(page.locator('#regelwerkSearchResults a').first).to_be_visible()
        page.locator('#regelwerkSearchResults a').first.click()
        expect(page.locator('#regelwerkArticle')).to_contain_text('Fireball')
        page.goto(origin + '/regelwerk/compendium?locale=en&type=spell&q=Fireball')
        expect(page.locator('#cpBody')).to_contain_text('Fireball')
        page.locator('#cpBody').get_by_role('link', name='Fireball', exact=True).click()
        expect(page.locator('#cpDetail')).to_contain_text('8d6')
        assert 'locale=en' in page.url
        expect(page.locator('.cp-character-actions-entry button')).to_have_count(0)
        page.reload()
        expect(page.locator('#cpDetail')).to_contain_text('Fireball')
        page.goto(origin + '/regelwerk/5.2.1/de/w20-pruefungen')
        expect(page.locator('#regelwerkArticle')).to_contain_text('W20')
        assert '/de/' in page.url
        page.goto(origin + '/regelwerk/compendium?locale=de&type=spell&q=Feuerball')
        expect(page.locator('#cpBody')).to_contain_text('Feuerball')
        assert page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 1
        assert not errors, errors
        browser.close()
