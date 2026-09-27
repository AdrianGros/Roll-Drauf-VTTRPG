"""Real authenticated REST/socket commands and the three browser editing modes."""

import os
from pathlib import Path
from threading import Thread

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token
from flask_socketio import SocketIO
from werkzeug.serving import make_server

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.transports import register

from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author, decision, read, wire

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def transport(author, request):
    profile = getattr(request, "param", None)
    if profile == "damage-native":
        from test_ce_native import native_world
        author = native_world(author, damage=True)
    elif profile == "native":
        from vtt.creation_engine.transports.legacy_host import build_gateway
        author = dict(author)
        author["gateway"] = build_gateway(author["gateway"].store.engine, native_authoring=True)
        author["service"] = author["gateway"].authoring
    app = Flask("ce-authoring", template_folder=str(ROOT / "vtt/templates"), static_folder=str(ROOT / "vtt/static"))
    app.config.update(TESTING=True, SECRET_KEY="test-authoring-secret-" * 3, JWT_SECRET_KEY="test-authoring-jwt-" * 3,
        JWT_TOKEN_LOCATION=["cookies"], JWT_COOKIE_CSRF_PROTECT=True, CE_AUTHORING=True, CE_RUNTIME=bool(profile))
    JWTManager(app)
    sockets = SocketIO(app, async_mode="threading")
    app.extensions["ce_gateway"] = author["gateway"]
    register(app, sockets)
    with app.app_context():
        token = create_access_token(identity=str(author["principal"]))
        csrf = decode_token(token)["csrf"]
    client = app.test_client()
    client.set_cookie("access_token_cookie", token)
    client.set_cookie("csrf_access_token", csrf)
    return app, sockets, client, token, csrf, author


def path(author):
    return f"/api/ce/authoring/workspaces/{author['workspace']}/drafts/{author['draft']}"


def test_authoring_is_flagged_authenticated_and_private(transport):
    app, _, client, _, csrf, author = transport
    assert app.test_client().get(path(author)).status_code == 401
    response = client.get(path(author))
    assert response.status_code == 200 and response.headers["Cache-Control"] == "private, no-store"
    command = wire(author, "RecordDraftDecision", decision("item.name", "HTTP draft"))
    assert client.post('/api/ce/commands', data=canonical_bytes(command)).status_code == 401
    result = client.post('/api/ce/commands', data=canonical_bytes(command), headers={"X-CSRF-TOKEN": csrf})
    assert result.status_code == 200 and read(author)["content"]["name"] == "HTTP draft"
    assert client.get(path(author), headers={"X-CE-View-As": "view:pretend"}).status_code == 403
    app.config.update(CE_AUTHORING=False, CE_RUNTIME=True)
    assert client.get(path(author)).status_code == 404
    assert client.post('/api/ce/commands', data=canonical_bytes(command), headers={"X-CSRF-TOKEN": csrf}).status_code == 404


def test_unmet_quality_returns_safe_actionable_gates(transport):
    _, _, client, _, csrf, author = transport
    command = wire(author, "CommitDraftRevision", {"declaredQuality": "runtime_ready", "definition": {"kind": "new"}})
    response = client.post('/api/ce/commands', data=canonical_bytes(command), headers={"X-CSRF-TOKEN": csrf})
    assert response.status_code == 409 and response.json["error"]["code"] == "QUALITY_CLAIM_UNMET"
    assert {g["code"] for g in response.json["error"]["gates"]} >= {"ANSWER_REQUIRED", "RUNTIME_REGISTRATION_PENDING"}
    assert read(author)["draftVersion"] == 1


def test_socket_retry_of_rest_decision_shares_receipt_and_version(transport):
    app, sockets, client, _, csrf, author = transport
    command = wire(author, "RecordDraftDecision", decision("item.name", "One command, two transports"))
    result = client.post('/api/ce/commands', data=canonical_bytes(command), headers={"X-CSRF-TOKEN": csrf})
    socket = sockets.test_client(app, flask_test_client=client, namespace="/creation-engine", auth={"csrf": csrf})
    try:
        assert socket.is_connected('/creation-engine')
        retry = socket.emit("ce:command", {"command": canonical_bytes(command).decode()}, namespace="/creation-engine", callback=True)
        assert retry == result.json and read(author)["draftVersion"] == 2
    finally:
        socket.disconnect(namespace='/creation-engine')


@pytest.fixture
def browser(transport, request):
    playwright = pytest.importorskip("playwright.sync_api")
    app, _, _, token, csrf, author = transport
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with playwright.sync_playwright() as p:
            browser_name = getattr(request, "param", "chromium")
            browser = getattr(p, browser_name).launch(headless=True, args=["--no-sandbox"] if browser_name == "chromium" else [])
            context = browser.new_context(viewport={"width": 1280, "height": 960})
            context.add_cookies([{"name": "access_token_cookie", "value": token, "url": origin, "httpOnly": True},
                                {"name": "csrf_access_token", "value": csrf, "url": origin}])
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + '/api/ce/authoring')
            page.wait_for_function("document.getElementById('draft-info').textContent.length > 0 && !document.getElementById('mode').disabled")
            yield page, author
            assert errors == []
            browser.close()
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()


def wait_version(page, version):
    page.wait_for_function("v => document.getElementById('draft-info').textContent.endsWith(' ' + v) && !document.getElementById('mode').disabled", arg=version)


def test_browser_modes_locales_stale_answers_and_revision(browser, tmp_path):
    page, author = browser
    assert page.locator('form').get_attribute('data-question') == 'flame.behavior'
    page.locator('#damage-preset').click()
    page.locator('#preset').wait_for(state='visible')
    assert len(page.locator('#preset-values pre').all()) == 11
    assert read(author)['draftVersion'] == 1
    page.locator('#apply-preset').click(); wait_version(page, 2)
    page.locator('#mode').select_option('advanced')
    page.locator('form[data-question="flame.cost"] textarea').wait_for()
    page.locator('#locale').select_option('en')
    page.get_by_role('button', name='Save answer', exact=True).first.wait_for()
    form = page.locator('form[data-question="flame.cost"]')
    form.locator('textarea').fill('2')
    assert page.locator('#locale').is_disabled()
    form.get_by_role('button', name='Save answer', exact=True).click(); wait_version(page, 3)
    assert read(author)['content']['flames']['cost'] == 2
    page.locator('#mode').select_option('structured')
    page.locator('form[data-question="flame.behavior"] select').wait_for()
    page.locator('#locale').select_option('fr')
    page.get_by_role('button', name='Enregistrer la réponse', exact=True).first.wait_for()
    form = page.locator('form[data-question="flame.behavior"]')
    form.locator('select').select_option('visual')
    form.get_by_role('button', name='Enregistrer la réponse', exact=True).click(); wait_version(page, 4)
    assert 'damage' not in read(author)['content']['flames'] and page.locator('#stale').is_visible()
    page.locator('#claim').select_option('runtime_ready')
    assert page.locator('#commit').is_disabled()
    page.locator('#claim').select_option('sheet_ready')
    page.locator('#commit').click(); wait_version(page, 5)
    assert 'rev:' in page.locator('#revision').inner_text()
    page.locator('#mode').select_option('guided')
    page.locator('form[data-question="flame.timing"]').wait_for()
    page.locator('#locale').select_option('de')
    page.get_by_role('button', name='Antwort speichern', exact=True).wait_for()
    assert read(author)['draftVersion'] == 5
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path))
    artifact.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(artifact / 'authoring-editor.png'), full_page=True)


def test_browser_lost_response_retries_same_command_once(browser):
    page, author = browser
    page.locator('#mode').select_option('structured')
    form = page.locator('form[data-question="item.name"]')
    form.locator('textarea').fill('<img src=x onerror=alert(1)> Harmless')
    requests = []
    def response_lost(route):
        requests.append(route.request.post_data_json)
        if len(requests) == 1:
            route.fetch()
            route.abort('failed')
        else:
            route.continue_()
    page.route('**/api/ce/commands', response_lost)
    form.get_by_role('button', name='Antwort speichern', exact=True).click()
    page.locator('#retry').wait_for(state='visible')
    assert read(author)['draftVersion'] == 2
    page.locator('#retry').click(); wait_version(page, 2)
    assert len(requests) == 2 and requests[0] == requests[1]
    assert read(author)['draftVersion'] == 2 and page.locator('#content img').count() == 0
    assert '<img' in page.locator('#content').inner_text()


@pytest.mark.parametrize('transport', ['native'], indirect=True)
def test_browser_authors_commits_instantiates_and_runs_harmless_flames(browser):
    page, author = browser
    page.locator('#visual-preset').click(); page.locator('#apply-preset').click(); wait_version(page, 2)
    page.locator('#claim').select_option('runtime_ready')
    assert page.locator('#commit').is_enabled()
    page.locator('#commit').click(); wait_version(page, 3)
    page.locator('#sb-revisions input').check()
    page.locator('#sb-create').click()
    page.locator('#sb-scope').wait_for(state='visible')
    page.locator('#sb-revision').select_option(index=1)
    page.locator('#sb-reason').fill('Isolated cosmetic test')
    page.locator('#sb-instantiate').click()
    page.wait_for_function("document.querySelectorAll('#sb-item option').length === 2 && !document.getElementById('sb-item').disabled")
    page.locator('#sb-item').select_option(index=1)
    page.locator('#sb-activate').click()
    page.locator('#sb-instances li').filter(has_text='2/3').wait_for()
    page.locator('#sb-recover').click()
    page.locator('#sb-instances li').filter(has_text='3/3').wait_for()
    scope_id = page.locator('#sb-select').input_value()
    summary = author['gateway'].kernel.native.summary(author['gateway'], author['principal'], scope_id)
    assert len(summary['instances']) == 1 and summary['activeAction'] is None


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_optional_damage_choice_updates_only_committed_target(browser):
    page, author = browser
    page.locator('#sb-select').select_option(author['scope'])
    page.locator('#sb-scope').wait_for(state='visible')
    page.locator('#sb-item').select_option(author['item'])
    page.locator('#sb-target').select_option(author['target'])
    page.locator('#sb-hit').click()
    page.get_by_role('button', name='Ja, Ladungen ausgeben', exact=True).click()
    page.locator('#sb-instances li').filter(has_text='14/30').wait_for()
    assert page.locator('#sb-instances li').filter(has_text='20/30').count() == 1
    assert page.locator('#sb-instances li').filter(has_text='2/3').count() == 1
    assert author['gateway'].kernel.random.draws == 2
