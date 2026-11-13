"""Prerequisites are authoritative in evaluation, finalization and progression."""
import copy

import pytest

from tests.test_srd_creator_api import BASE, app, client, data, make_draft  # noqa: F401
from tests.test_srd_progression import level_one_state, payload_from_needs
from vtt.characters import srd_progression
from vtt.rules_content.creator_rules import class_option_eligibility, evaluate

PREFIX = 'classes.warlock.invocation-'


def warlock(data, level=5):
    state = level_one_state(data, 'warlock')
    for _ in range(1, level):
        evaluation = evaluate(data, state)
        need = srd_progression.needs(data, state, evaluation, 'warlock')
        state = srd_progression.build_state(data, state, payload_from_needs(data, need, evaluation, state))
    return state


def verdict(data, state, option, level=5):
    return class_option_eligibility(data, state, 'warlock', level)[PREFIX + option]


@pytest.mark.parametrize('option,dependency,level', [
    ('eldritch-smite', 'pact-of-the-blade', 5),
    ('lifedrinker', 'pact-of-the-blade', 9),
    ('thirsting-blade', 'pact-of-the-blade', 5),
    ('chains-blessing', 'pact-of-the-chain', 5),
    ('gift-of-the-protectors', 'book-of-shadows', 9),
    ('improved-pact-weapon', 'thirsting-blade', 12),
])
def test_pact_dependencies_are_required_and_transitive(data, option, dependency, level):
    state = warlock(data)
    picks = state['featureChoices']['warlock']['eldritch-invocations'] = []
    assert not verdict(data, state, option, level)['eligible']
    picks.append(PREFIX + dependency)
    if dependency == 'thirsting-blade':
        assert not verdict(data, state, option, level)['eligible']
        picks.append(PREFIX + 'pact-of-the-blade')
    assert verdict(data, state, option, level)['eligible']
    assert not verdict(data, state, option, level - 1)['eligible']


@pytest.mark.parametrize('option', ['agonizing-blast', 'eldritch-spear', 'repelling-blast'])
def test_only_a_known_warlock_damage_cantrip_qualifies(data, option):
    state = warlock(data)
    state['spells']['warlock']['cantrips'] = ['spells.m-p.magierhand', 'spells.c-e.einfache-illusion']
    state['spells']['wizard'] = {'cantrips': ['spells.r-s.schauriger-strahl']}
    assert not verdict(data, state, option)['eligible']
    state['spells']['warlock']['cantrips'].append('spells.f-g.feuerpfeil')
    assert not verdict(data, state, option)['eligible']
    for spell in ['spells.f-g.gift-verspruehen', 'spells.h-l.kalte-hand',
                  'spells.r-s.schauriger-strahl', 'spells.w-z.zielsicherer-schlag']:
        state['spells']['warlock']['cantrips'] = [spell]
        assert verdict(data, state, option)['eligible'], spell


def test_minimum_is_class_level_and_inactive_buckets_do_not_qualify(data):
    state = warlock(data)
    state['featureChoices']['warlock'] = {'wrong-bucket': [PREFIX + 'pact-of-the-blade']}
    assert not verdict(data, state, 'eldritch-smite')['eligible']
    state['featureChoices']['warlock']['eldritch-invocations'] = [PREFIX + 'pact-of-the-blade']
    state['levels'] = [{'classKey': 'warlock'}] * 4 + [{'classKey': 'fighter'}] * 8
    evaluation = evaluate(data, state)
    assert not evaluation['classOptionEligibility']['warlock'][PREFIX + 'eldritch-smite']['eligible']


def test_attack_requirement_is_stricter_than_damage_requirement(data):
    # Synthetic metadata tests the predicate distinction; it does not change SRD content.
    altered = copy.deepcopy(data)
    sid = 'spells.r-s.schauriger-strahl'
    altered['spells'][sid]['invocationCantrip']['attack'] = False
    state = warlock(data)
    state['spells']['warlock']['cantrips'] = [sid]
    assert verdict(altered, state, 'agonizing-blast')['eligible']
    assert not verdict(altered, state, 'repelling-blast')['eligible']


def test_generator_fails_closed_for_unparsed_requirements(data):
    from vtt.rules_content.creator_data import _class_options
    entity = {'type': 'class-option', 'id': 'test-option', 'name': 'Test', 'classKey': 'warlock', 'optionKind': 'invocation',
              'prerequisite': 'Ab 2. Hexenmeisterstufe, unparsed requirement'}
    with pytest.raises(ValueError, match='unparsed class-option prerequisite'):
        _class_options([entity], None)


def test_invalid_invocation_is_saved_readable_but_cannot_finalize(client, data):
    state = warlock(data)
    state['featureChoices']['warlock']['eldritch-invocations'] = [PREFIX + x for x in
        ['eldritch-mind', 'devils-sight', 'fiendish-vigor', 'ascendant-step', 'eldritch-smite']]
    before = copy.deepcopy(state)
    created = make_draft(client, state)
    assert created['draft']['state'] == before
    assert any(b['code'] == 'class-option-prerequisite' for b in created['blockers'])
    draft = created['draft']
    response = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={'version': draft['version']})
    assert response.status_code == 422
    assert any(b['code'] == 'class-option-prerequisite' for b in response.get_json()['blockers'])


def test_level_up_cannot_bypass_prerequisites(client, data):
    state = warlock(data, 4)
    state['featureChoices']['warlock']['eldritch-invocations'] = [PREFIX + x for x in
        ['eldritch-mind', 'devils-sight', 'fiendish-vigor']]
    draft = make_draft(client, state)['draft']
    char = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={'version': draft['version']})
    assert char.status_code == 201, char.get_json()
    cid = char.get_json()['character']['id']
    assert client.put(f'{BASE}/characters/{cid}/progression', json={'mode': 'milestone', 'milestoneTarget': 5}).status_code == 200
    payload = {'classKey': 'warlock', 'hp': 'fixed', 'expectedLevel': 4, 'featureChoices': {'eldritch-invocations':
        state['featureChoices']['warlock']['eldritch-invocations'] + [PREFIX + 'ascendant-step', PREFIX + 'eldritch-smite']}}
    need = srd_progression.needs(data, state, evaluate(data, state), 'warlock')
    payload['spells'] = payload_from_needs(data, need, evaluate(data, state), state)['spells']
    preview = client.post(f'{BASE}/characters/{cid}/level-up/preview', json=payload)
    assert preview.status_code == 200
    assert any(b['code'] == 'class-option-prerequisite' for b in preview.get_json()['blockers'])
    result = client.post(f'{BASE}/characters/{cid}/level-up', json=payload)
    assert result.status_code == 422
    payload['featureChoices']['eldritch-invocations'][-2] = PREFIX + 'pact-of-the-blade'
    valid = client.post(f'{BASE}/characters/{cid}/level-up/preview', json=payload)
    assert valid.status_code == 200
    assert valid.get_json()['blockers'] == []
