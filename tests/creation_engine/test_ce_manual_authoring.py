"""Persisted manual profiles and real browser task journeys in isolated PostgreSQL."""

import json
import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.compiler import catalog, manual
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.transports.legacy_host import build_gateway

from test_ce_authoring_transports import author, authoring_engine, browser, migration_engine, postgres_engine, transport, wait_version
from test_ce_authoring import read, submit, wire
from test_ce_manual_compiler import ANSWERS

pytestmark = pytest.mark.postgres


def create(a, kind):
    _, result = submit(a, "CreateDraft", {"schemaType": kind.to_wire(), "authoringLocale": "en"})
    return {**a, "draft": result["draftId"]}


def answer(a, key, value):
    kind = next(kind for kind in manual.TYPES if kind.to_wire() == read(a)["schemaType"])
    q = catalog.guide_for(kind).by_id[key]
    return submit(a, "RecordDraftDecision", {"question": {"questionId": key, "questionVersion": 1},
        "answer": q.answer(value), "promptLocale": "en"})


@pytest.mark.parametrize("kind", manual.TYPES)
def test_manual_drafts_persist_revision_and_reject_runtime_without_changing_flame(author, kind):
    before = read(author)
    a = create(author, kind)
    for key, value in ANSWERS[kind].items():
        answer(a, key, value)
    quality = "lore_only" if kind == manual.LORE else "sheet_ready"
    _, result = submit(a, "CommitDraftRevision", {"declaredQuality": quality, "definition": {"kind": "new"}})
    with Session(a["gateway"].store.engine) as session:
        revision = ContentStore(session).revision(result["revision"]["id"])
        assert revision.content == read(a)["content"]
        assert parse_strict_json(revision.provenance)["registry"] == catalog.registry(kind).artifact()
    saved_version = read(a)["draftVersion"]
    native = build_gateway(a["gateway"].store.engine, native_authoring=True)
    a = {**a, "gateway": native, "service": native.authoring}
    for claim in ("runtime_ready", "automation_complete"):
        with pytest.raises(ContractViolation, match="QUALITY_CLAIM_UNMET"):
            submit(a, "CommitDraftRevision", {"declaredQuality": claim, "definition": {"kind": "new"}})
    assert read(a)["draftVersion"] == saved_version
    assert result["revision"]["id"] not in {r["revision"]["id"] for r in native.kernel.native.catalog(a["principal"])["revisions"]}
    sandbox_command = {**wire(a, "CreateDraft", {"ruleset": native.kernel.ruleset.artifact(), "revisions": [result["revision"]]}),
                       "operation": "CreateSandboxScope"}
    with pytest.raises(ContractViolation):
        native.submit(a["principal"], canonical_bytes(sandbox_command))
    assert read(author) == before
    # The existing owner boundary also applies to the new profiles.
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        a["service"].read(a["principal"] + 100000, a["workspace"], a["draft"])


def test_wrong_profile_preset_is_rejected_atomically_and_own_retry_is_exact(author):
    a = create(author, manual.CHOICE)
    before = read(a)
    preview = a["service"].preview(a["principal"], a["workspace"], "g1.harmless-flames")
    with pytest.raises(ContractViolation, match="SEMANTIC_INVALID"):
        submit(a, "ApplyDraftPreset", {"preset": {"presetId": "g1.harmless-flames", "version": 1}, "previewDigest": preview["previewDigest"]})
    assert read(a) == before
    command = wire(a, "RecordDraftDecision", {"question": {"questionId": "content.name", "questionVersion": 1},
        "answer": {"kind": "text", "value": "Two paths"}, "promptLocale": "en"})
    first = a["gateway"].submit(a["principal"], canonical_bytes(command))
    assert a["gateway"].submit(a["principal"], canonical_bytes({**command, "commandId": new_id("cmd")})) == first
    assert read(a)["draftVersion"] == 2


def test_choice_invalid_quality_then_revert_restores_answers_with_history(author):
    a = create(author, manual.CHOICE)
    for key, value in ANSWERS[manual.CHOICE].items():
        answer(a, key, value)
    complete = read(a)
    answer(a, "choice.count", 3)
    assert "alternatives" not in read(a)["content"]["choice"]
    with pytest.raises(ContractViolation, match="QUALITY_CLAIM_UNMET"):
        submit(a, "CommitDraftRevision", {"declaredQuality": "sheet_ready", "definition": {"kind": "new"}})
    submit(a, "RevertDraft", {"toDraftVersion": complete["draftVersion"]})
    assert read(a)["content"] == complete["content"]
    assert read(a)["draftVersion"] == complete["draftVersion"] + 2


@pytest.mark.parametrize("kind", manual.TYPES)
@pytest.mark.parametrize("locale", ["de", "en", "fr"])
def test_browser_authors_manual_task_in_all_modes_and_saves_honest_revision(browser, kind, locale, tmp_path):
    page, author = browser
    page.locator('#locale').select_option(locale)
    page.wait_for_function("!document.getElementById('new-type').disabled")
    page.locator('#new-type').select_option(kind.type_id)
    page.locator('#new').click(); wait_version(page, 1)
    assert page.locator('#profile-notice').is_visible()
    assert page.locator('#presets-section').is_hidden()
    draft_id = page.locator('#drafts').input_value()
    a = {**author, "draft": draft_id}
    modes = ("guided", "structured", "advanced")
    for index, (key, value) in enumerate(ANSWERS[kind].items()):
        mode = modes[index % 3]
        # Structured/Advanced support arbitrary order; Guided follows priorities.
        if mode == "guided" and read(a)["nextQuestionId"] != key:
            mode = "structured"
        page.locator('#mode').select_option(mode)
        form = page.locator(f'form[data-question="{key}"]')
        field = form.locator('textarea, input, select').first
        if mode == "advanced":
            field.fill(json.dumps(value))
        else:
            field.fill(str(value))
        if index == 0:
            assert page.locator('#new-type').is_disabled()
        form.locator('button[type="submit"]').click(); wait_version(page, index + 2)
    page.locator('#claim').select_option('runtime_ready')
    assert page.locator('#commit').is_disabled()
    page.locator('#claim').select_option('lore_only' if kind == manual.LORE else 'sheet_ready')
    assert page.locator('#commit').is_enabled()
    page.locator('#commit').click(); wait_version(page, len(ANSWERS[kind]) + 2)
    assert page.locator('#revision').inner_text()
    page.reload(); wait_version(page, len(ANSWERS[kind]) + 2)
    assert read(a)["content"]["name"] == ANSWERS[kind]["content.name"]
    page.locator('#locale').select_option(locale)
    page.wait_for_function("!document.getElementById('locale').disabled")
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator('#mode').select_option('structured')
    page.wait_for_function("!document.getElementById('mode').disabled")
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path)); artifact.mkdir(exist_ok=True, parents=True)
    page.screenshot(path=str(artifact / (kind.type_id + '-' + locale + '-phone.png')), full_page=True)


@pytest.mark.parametrize('browser', ['webkit'], indirect=True)
@pytest.mark.skipif(os.environ.get('CE_TEST_WEBKIT') != '1', reason='Set CE_TEST_WEBKIT=1 on a host with the Playwright WebKit system libraries')
def test_webkit_manual_choice_keyboard_save_and_phone_reflow(browser):
    page, _ = browser
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#new-type').select_option(manual.CHOICE.type_id)
    page.locator('#new').focus(); page.keyboard.press('Enter'); wait_version(page, 1)
    field = page.locator('form[data-question="content.name"] textarea')
    field.fill('Wegwahl')
    page.keyboard.press('Tab'); page.keyboard.press('Enter'); wait_version(page, 2)
    assert 'Wegwahl' in page.locator('#draft-info').inner_text()
    assert page.locator('form[data-question="choice.prompt"] textarea').evaluate('(n) => n === document.activeElement')
    page.locator('#mode').select_option('advanced')
    page.wait_for_function("!document.getElementById('mode').disabled")
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
