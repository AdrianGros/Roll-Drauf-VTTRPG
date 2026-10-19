"""Author executable homebrew through actual fields, without writing JSON."""
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

from homebrew_examples import examples
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author, read, submit
from test_ce_authoring_transports import transport, browser, wait_version
from test_ce_homebrew_backend import homebrew_tables
from test_ce_advanced import created, payload, save
from vtt.creation_engine.compiler import homebrew as h

pytestmark = pytest.mark.postgres


def field(page, path):
    return page.locator('.ce-schema-node[data-path="'+path+'"]')


def enter(page, schema, value, path):
    node = field(page, path)
    if 'const' in schema:
        return
    if 'oneOf' in schema:
        def matches(branch):
            if branch.get('type') == 'null': return value is None
            if branch.get('type') == 'object': return isinstance(value, dict) and value.get('kind') == branch.get('properties',{}).get('kind',{}).get('const')
            return isinstance(value,str) and branch.get('type') == 'string'
        index = next(i for i,branch in enumerate(schema['oneOf']) if matches(branch))
        node.locator(':scope > label > select[data-value]').select_option(str(index))
        enter(page,schema['oneOf'][index],value,path+'/variant'+str(index))
    elif schema.get('type') == 'null':
        return
    elif schema.get('type') == 'object':
        if not value:
            node.locator(':scope > button[data-action="none"]').click()
        for key,item in value.items():
            if key not in schema.get('required',[]):
                node.locator(':scope > label > select[data-optional]').select_option(key)
                node.locator(':scope > button[data-action="add-field"]').click()
            enter(page,schema['properties'][key],item,path+'/'+key)
    elif schema.get('type') == 'array':
        if not value:
            node.locator(':scope > button[data-action="none"]').click()
        for i,item in enumerate(value):
            node.locator(':scope > button[data-action="add"]').click()
            enter(page,schema['items'],item,path+'/'+str(i))
    elif 'enum' in schema or schema.get('type')=='boolean':
        index=(schema.get('enum') or [True,False]).index(value)
        node.locator(':scope > label > select[data-value]').select_option(str(index))
    else:
        node.locator(':scope > label > [data-value]').fill(str(value))


def create(page, kind):
    page.locator('#new-type').select_option(kind.type_id)
    page.locator('#new').click()
    wait_version(page,1)
    return page.locator('#drafts').input_value()


def author_document(page,a,kind,document):
    draft_id=create(page,kind)
    a={**a,'draft':draft_id}
    count=1
    for _ in range(len(h.interview(kind).questions)):
        question_id=page.locator('#questions form').get_attribute('data-question')
        q=h.interview(kind).by_id[question_id]
        value=document
        for key in q.path:
            if key not in value:
                assert not q.required
                page.locator('#questions form').get_by_role('button',name='Skip',exact=True).click()
                break
            value=value[key]
        else:
            enter(page,q.schema,value,'/'.join(q.path))
            page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click()
        count+=1;wait_version(page,count)
    assert read(a)['content']==document
    page.locator('#claim').select_option('runtime_ready')
    page.locator('#commit').click();count+=1;wait_version(page,count)
    expect(page.locator('#revision')).to_contain_text('rev:')
    return a,count


def test_guided_authors_class_race_spell_and_reopens_in_advanced(browser,tmp_path):
    page,a=browser
    page.locator('#locale').select_option('en')
    page.wait_for_function("!document.getElementById('mode').disabled")
    documents=examples()[:3]
    documents[0][1]['class']['levels'][0]['features'][0]['grants']['spells']=['ember']
    documents[0][1]['class']['levels'][0]['features'][0]['description']=''
    for kind,document in documents:
        a,count=author_document(page,a,kind,document)
        expect(page.locator('#questions-complete')).to_be_visible()
        expect(page.locator('#guided-progress')).to_contain_text('Required answers')
        assert page.locator('#content pre').count()==0
    page.locator('#guided-progress summary').click()
    page.locator('[data-review="spell.effect"]').click()
    effect=field(page,'spell/effect')
    branch=effect.locator(':scope > label > select[data-value]')
    # Switching variants preserves unsaved input; only the selected branch submits.
    field(page,'spell/effect/variant0/dice/bonus').locator('input').fill('4')
    branch.select_option('1')
    branch.select_option('0')
    expect(field(page,'spell/effect/variant0/dice/bonus').locator('input')).to_have_value('4')
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click()
    count+=1;wait_version(page,count)
    assert read(a)['content']['spell']['effect']['dice']['bonus']==4
    page.locator('#guided-progress summary').click()
    page.locator('[data-review="spell.effect"]').click()
    folder=Path(os.environ.get('CE_TEST_ARTIFACT_DIR',tmp_path));folder.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(folder/'guided-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(folder/'guided-mobile.png'),full_page=True)
    page.locator('#homebrew-test-link a').click()
    expect(page.locator('#source')).to_be_enabled()
    assert json.loads(page.locator('#source').input_value())==read(a)['content']
    page.locator('#test-tab').click()
    expect(page.locator('#edition')).to_be_enabled()
    page.locator('#edition').select_option('dnd5e_2024')
    expect(page.locator('#revision-list input')).to_have_count(3)


def test_guided_empty_values_are_not_inferred_and_locale_changes_keep_answers(browser):
    page,a=browser
    page.locator('#locale').select_option('en')
    page.wait_for_function("!document.getElementById('mode').disabled")
    a={**a,'draft':create(page,h.CLASS)}
    expect(page.locator('#questions input')).to_have_value('')
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click()
    assert read(a)['draftVersion']==1 and not read(a)['content']
    page.locator('#questions input').fill('Test class')
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click();wait_version(page,2)
    expect(page.locator('#questions select')).to_have_value('')
    for locale in ['de','fr','en']:
        page.locator('#locale').select_option(locale)
        page.wait_for_function("!document.getElementById('mode').disabled")
        assert read(a)['content']=={'name':'Test class'}
        expect(page.locator('#questions select')).to_have_value('')


def test_nested_conflict_restores_the_entire_local_variant_and_retries_once(browser):
    page,a=browser
    kind,document=examples()[2]
    a=created(a,kind);save(a,payload(a,document))
    page.locator('#reload').click()
    page.wait_for_function("!document.getElementById('mode').disabled")
    page.locator('#locale').select_option('en')
    page.wait_for_function("!document.getElementById('mode').disabled")
    page.locator('#drafts').select_option(a['draft']);wait_version(page,2)
    page.locator('#guided-progress summary').click()
    page.locator('[data-review="spell.effect"]').click()
    variant=field(page,'spell/effect').locator(':scope > label > select[data-value]')
    variant.select_option('2')
    schema=h.interview(kind).by_id['spell.effect'].schema['oneOf'][2]
    enter(page,schema,{'kind':'modifier','stat':'ac','amount':3},'spell/effect/variant2')
    remote={**document,'name':'Changed in another tab'}
    save(a,payload(a,remote))
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click()
    expect(page.locator('#conflict')).to_be_visible()
    page.locator('#conflict-refresh').click()
    expect(page.locator('#conflict-edit')).to_be_visible()
    page.locator('#conflict-edit').click()
    expect(field(page,'spell/effect').locator(':scope > label > select[data-value]')).to_have_value('2')
    expect(field(page,'spell/effect/variant2/amount').locator('input')).to_have_value('3')
    expect(page.locator('#mode')).to_have_value('guided')
    requests=[]
    def lose(route):
        requests.append(route.request.post_data_json)
        if len(requests)==1:
            route.fetch();route.abort('failed')
        else:route.continue_()
    page.route('**/api/ce/commands',lose)
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click()
    expect(page.locator('#retry')).to_be_visible()
    page.locator('#retry').click();wait_version(page,4)
    assert requests[0]==requests[1] and len(requests)==2
    assert read(a)['content']['spell']['effect']=={'kind':'modifier','stat':'ac','amount':3}
    assert read(a)['content']['name']==remote['name']
    assert read(a)['qualityGates']['runtime_ready'] # Duration must now be authored for a modifier.


def test_nested_arrays_remove_optional_fields_and_enforce_explicit_empty(browser):
    page,a=browser
    a=created(a,h.CLASS);doc=examples()[0][1];save(a,payload(a,doc))
    page.locator('#reload').click()
    page.wait_for_function("!document.getElementById('mode').disabled")
    page.locator('#locale').select_option('en')
    page.wait_for_function("!document.getElementById('mode').disabled")
    page.locator('#drafts').select_option(a['draft']);wait_version(page,2)
    page.locator('#guided-progress summary').click()
    page.locator('[data-review="class.levels"]').click()
    # Remove the second level and all level-one features, then save the explicit empty list.
    levels=field(page,'class/levels')
    levels.locator(':scope > div > section > button[data-action="remove"]').last.click()
    features=field(page,'class/levels/0/features')
    features.locator(':scope > button[data-action="none"]').click()
    page.locator('#questions form').get_by_role('button',name='Save answer',exact=True).click();wait_version(page,3)
    assert read(a)['content']['class']['levels']==[{'level':1,'hpGain':8,'features':[]}]


def test_guided_access_loss_clears_nested_input_and_progress(browser):
    page,_=browser
    create(page,h.CLASS)
    page.locator('#questions input').fill('Private unsaved class')
    page.route('**/api/ce/authoring/workspace',lambda route:route.fulfill(status=401,json={'error':{'code':'UNAUTHORIZED'}}))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator('#questions')).to_have_text('')
    expect(page.locator('#guided-progress')).to_have_text('')
    expect(page.locator('#content')).to_have_text('')
    expect(page.locator('#editor')).to_be_hidden()
