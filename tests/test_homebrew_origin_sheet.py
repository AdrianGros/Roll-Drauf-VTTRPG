"""Character-facing D&D rules render as text, with existing sheet content preserved."""

from copy import deepcopy
from pathlib import Path
import re

import pytest


playwright = pytest.importorskip('playwright.sync_api')
expect = playwright.expect
TEMPLATE = Path(__file__).resolve().parents[1] / 'vtt/templates/character-sheet.html'


@pytest.fixture(scope='module')
def sheet_browser():
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=['--no-sandbox'])
        yield browser
        browser.close()


@pytest.fixture
def page(sheet_browser):
    """Mount the actual sheet template and scripts without the unrelated book animation."""
    page = sheet_browser.new_page(viewport={'width': 900, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    template = TEMPLATE.read_text(encoding='utf-8')
    inline_script = re.search(r'<script>\s*(.*?)\s*</script>', template, re.S).group(1)
    markup = re.sub(r'<script\b[^>]*>.*?</script>', '', template, flags=re.S)
    page.set_content(markup)
    page.add_script_tag(content='class Auth {}')
    page.add_script_tag(content=inline_script)
    page.evaluate("""() => {
        document.body.prepend(document.getElementById('characterSheetSceneTemplate').content.cloneNode(true));
        document.getElementById('characterSheetSceneStatus').hidden = true;
    }""")
    yield page
    assert errors == []
    page.close()


@pytest.fixture
def character():
    return {
        'id': 42, 'name': 'Mara', 'system_id': 'dnd5e', 'race': 'Stormkin',
        'homebrew_origin': {
            'name': 'Stormkin', 'edition': 'dnd5e_2014', 'creatureType': 'Humanoid',
            'size': 'medium', 'speed': 35, 'languages': 'Common and one chosen language',
            'abilityScoreRules': 'Increase Dexterity by 2 and Wisdom by 1.',
            'prose': 'Children of the storm.\nThey travel in small groups.',
            'traits': [
                {
                    'name': 'Windborn', 'kind': 'trait', 'description': 'Ignore difficult terrain caused by snow.',
                    'usage': 'Always active', 'prerequisites': 'While walking',
                },
                {
                    'name': 'Storm Voice', 'kind': 'feature', 'description': 'Call a gust of wind.\nThe target makes a saving throw.',
                    'usage': 'Once per long rest', 'choices': 'Choose thunder or lightning when applying this feature.',
                    'prerequisites': 'Level 3',
                },
            ],
        },
    }


def render(page, character):
    page.evaluate("""character => {
        sheet = {character, spells: [], equipment: [], inventory: []};
        renderSheet();
    }""", character)


@pytest.mark.parametrize('edition,year', [('dnd5e_2014', '2014'), ('dnd5e_2024', '2024')])
def test_sheet_displays_complete_dnd_race_rules_and_manual_usage(page, character, edition, year):
    character['homebrew_origin']['edition'] = edition
    render(page, character)
    profile = page.locator('#homebrewOriginSection')
    expect(profile).to_be_visible()
    expect(page.locator('#sheetEmptyState')).to_be_hidden()
    expect(page.locator('#dndExportSection button')).to_be_visible()
    for text in [f'D&D 5e ({year})', 'Stormkin', 'Humanoid', 'Mittelgroß', '35 ft',
                 character['homebrew_origin']['languages'], character['homebrew_origin']['abilityScoreRules'],
                 'Children of the storm.', 'am Tisch manuell']:
        expect(profile).to_contain_text(text)
    cards = page.locator('#homebrewOriginTraits article')
    expect(cards).to_have_count(2)
    for index, trait in enumerate(character['homebrew_origin']['traits']):
        expect(cards.nth(index).locator('h3')).to_have_text(trait['name'])
        for key in ['description', 'usage', 'choices', 'prerequisites']:
            if key in trait:
                expect(cards.nth(index)).to_contain_text(trait[key])
    expect(cards.nth(0)).to_contain_text('Merkmal')
    expect(cards.nth(1)).to_contain_text('Feature')
    expect(page.locator('#srdSheetSection')).to_be_hidden()
    expect(page.locator('#charRace')).to_have_value('Stormkin')


def test_authored_html_remains_literal_in_every_rule_field(page, character):
    attack = '<img src=x onerror="window.homebrewExecuted=true">'
    origin = character['homebrew_origin']
    for key in ['name', 'prose', 'creatureType', 'size', 'languages', 'abilityScoreRules']:
        origin[key] = attack
    for trait in origin['traits']:
        for key in ['name', 'description', 'usage', 'choices', 'prerequisites']:
            trait[key] = attack
    render(page, character)
    expect(page.locator('#homebrewOriginProfile img, #homebrewOriginTraits img')).to_have_count(0)
    expect(page.locator('#homebrewOriginProfile h3')).to_have_text(attack)
    for card in page.locator('#homebrewOriginTraits article').all():
        expect(card.locator('h3')).to_have_text(attack)
        assert card.inner_text().count(attack) == 5
    assert page.evaluate('window.homebrewExecuted === undefined')


def test_refresh_replaces_race_rules_and_legacy_sheet_restores_its_sections(page, character):
    render(page, character)
    revised = deepcopy(character)
    revised['homebrew_origin']['traits'] = [revised['homebrew_origin']['traits'][1]]
    revised['homebrew_origin']['name'] = 'Revised Stormkin'
    render(page, revised)
    expect(page.locator('#homebrewOriginTraits article')).to_have_count(1)
    expect(page.locator('#homebrewOriginTraits')).not_to_contain_text('Windborn')
    render(page, {'id': 42, 'name': 'Legacy', 'system_id': None, 'race': 'Mensch'})
    expect(page.locator('#homebrewOriginSection')).to_be_hidden()
    expect(page.locator('#homebrewOriginTraitsSection')).to_be_hidden()
    expect(page.locator('#homebrewOriginTraits article')).to_have_count(0)
    expect(page.locator('#srdSheetSection')).to_be_hidden()
    expect(page.locator('#dndExportSection')).to_be_hidden()
    expect(page.locator('#charRace')).to_have_value('Mensch')


def test_sheet_navigation_carries_character_context_before_book_mount(sheet_browser):
    page = sheet_browser.new_page()
    template = TEMPLATE.read_text(encoding='utf-8')
    page.route('http://sheet.test/**', lambda route: route.fulfill(status=200, content_type='text/html', body='<body></body>'))
    page.goto('http://sheet.test/character-sheet?id=42')
    inline_script = re.search(r'<script>\s*(.*?)\s*</script>', template, re.S).group(1)
    page.set_content(re.sub(r'<script\b[^>]*>.*?</script>', '', template, flags=re.S))
    page.add_script_tag(content='class Auth {}; window.BookScene = {bootstrapProtectedRoute: async () => {}};')
    page.add_script_tag(content=inline_script)
    page.evaluate('bootstrapCharacterSheetScene()')
    links = page.evaluate("""() => [...document.getElementById('characterSheetSceneTemplate').content
        .querySelectorAll('[data-creation-engine-nav]')].map(link => link.dataset.creationEngineCharacterId)""")
    assert links == ['42', '42']
    page.close()


def test_dnd_size_choice_is_readable_and_plain_import_still_has_export(page, character):
    character['homebrew_origin']['size'] = 'small_or_medium'
    render(page, character)
    expect(page.locator('#homebrewOriginProfile')).to_contain_text('Klein oder mittelgroß (Auswahl)')
    render(page, {'id': 42, 'name': 'Plain import', 'system_id': 'dnd5e_2014', 'race': 'Human'})
    expect(page.locator('#homebrewOriginSection')).to_be_hidden()
    expect(page.locator('#dndExportSection button')).to_be_visible()
    expect(page.locator('#srdSheetSection')).to_be_hidden()
    expect(page.locator('#sheetEmptyState')).to_be_hidden()
