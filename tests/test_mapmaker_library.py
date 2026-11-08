"""Private project persistence, quota accounting and failure preservation."""
import base64
import io
import pytest
from flask_jwt_extended import create_access_token, decode_token
from PIL import Image
from vtt import create_app
from vtt.extensions import db
from vtt.mapmaker_document import normalize_document, known_assets
from vtt.models import Role, User
from vtt.models.mapmaker_project import MapmakerProject
from vtt.storage import LocalStorageAdapter
API = '/api/assets/mapmaker/projects'
GIB = 1024**3


def document(title='Testkarte'):
    image = io.BytesIO()
    Image.new('RGBA', (256, 256), (12, 45, 78, 255)).save(image, format='PNG')
    return {'format': 'rd-mapmaker', 'version': 1,
            'meta': {'title': title, 'seed': 1, 'showTitle': True},
            'size': {'w': 256, 'h': 256}, 'sea': {'top': '#123456', 'bottom': '#abcdef'},
            'layers': [
                {'id': 'r', 'name': 'Land', 'kind': 'raster', 'effects': {'coast': True},
                 'png': 'data:image/png;base64,' + base64.b64encode(image.getvalue()).decode()},
                {'id': 's', 'name': 'Symbole', 'kind': 'stamps', 'items': [
                    {'id': 'stamp1', 'asset': 'kenney:castle', 'x': 50, 'y': 60, 'size': 40,
                     'crop': {'x': 0, 'y': 0, 'w': 10, 'h': 10}}]},
                {'id': 'p', 'name': 'Wege', 'kind': 'paths', 'items': [
                    {'id': 'path1', 'x': 50, 'y': 60, 'material': 'river', 'width': 5,
                     'points': [{'x': 0, 'y': 0}, {'x': 20, 'y': 10}]}]},
                {'id': 't', 'name': 'Orte', 'kind': 'labels', 'items': [
                    {'id': 'town1', 'x': 50, 'y': 60, 'text': 'Küstenburg', 'style': 'town', 'size': 30,
                     'place': {'kind': 'castle', 'lore': 'Geheime Burg'},
                     'symbol': {'asset': 'builtin:castle', 'size': 40}}]},
            ]}


@pytest.fixture
def library(tmp_path):
    app = create_app('testing')
    app.config.update(LOCAL_STORAGE_PATH=str(tmp_path / 'storage'), STORAGE_PROVIDER='local', JWT_COOKIE_CSRF_PROTECT=True)
    with app.app_context():
        db.create_all()
        role = Role(name='Player')
        db.session.add(role)
        db.session.flush()
        users = []
        for name in ('map_owner', 'map_other', 'map_admin'):
            user = User(username=name, email=name+'@test.invalid', role_id=role.id,
                        password_hash='not-a-login', storage_quota_gb=1,
                        platform_role='admin' if name == 'map_admin' else None)
            db.session.add(user)
            users.append(user)
        db.session.commit()

        def client(user):
            token = create_access_token(identity=str(user.id))
            csrf = decode_token(token)['csrf']
            instance = app.test_client()
            instance.set_cookie('access_token_cookie', token)
            instance.set_cookie('csrf_access_token', csrf)
            return instance, {'X-Mapmaker-Account': str(user.id), 'X-CSRF-TOKEN': csrf}

        yield app, users, [client(user) for user in users], tmp_path / 'storage'
        db.session.remove()
        db.drop_all()


def create(library, doc=None):
    client, headers = library[2][0]
    response = client.post(API, json={'document': doc or document()}, headers=headers)
    assert response.status_code == 201, response.get_json()
    return response.get_json()['project']


def used(user):
    db.session.refresh(user)
    return round(user.storage_used_gb * GIB)


def test_roundtrip_editable_content_delta_quota_and_delete(library):
    _, users, clients, storage = library
    client, headers = clients[0]
    project = create(library)
    assert project['revision'] == 1
    assert used(users[0]) == project['sizeBytes']
    response = client.get(API + '/' + project['id'], headers=headers)
    assert response.status_code == 200
    saved = response.json['document']
    assert saved == normalize_document(document())[0]
    assert 'no-store' in response.headers['Cache-Control']
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    saved['meta']['title'] = 'Ausgebaut'
    saved['layers'][-1]['items'][0]['place']['lore'] += ' mit Markt und Hafen'
    updated = client.put(API + '/' + project['id'], json={'document': saved, 'revision': 1}, headers=headers)
    assert updated.status_code == 200
    project = updated.json['project']
    assert project['revision'] == 2
    assert used(users[0]) == project['sizeBytes']
    assert len(list(storage.rglob('*.json'))) == 1
    listed = client.get(API).json
    assert listed['total'] == 1 and listed['projects'][0]['title'] == 'Ausgebaut'
    assert listed['storage']['libraryBytes'] == project['sizeBytes']
    deleted = client.delete(API + '/' + project['id'], json={'revision': 2}, headers=headers)
    assert deleted.status_code == 200
    assert used(users[0]) == 0 and not list(storage.rglob('*.json'))


@pytest.mark.parametrize('outsider', [1, 2])
@pytest.mark.parametrize('method', ['get', 'put', 'delete'])
def test_foreign_projects_are_private_even_for_staff(library, outsider, method):
    project = create(library)
    client, headers = library[2][outsider]
    kwargs = {'headers': headers}
    if method != 'get': kwargs['json'] = {'revision': 1, 'document': document('Stolen')}
    assert getattr(client, method)(API + '/' + project['id'], **kwargs).status_code == 404
    assert client.get(API).json['total'] == 0
    assert used(library[1][0]) == project['sizeBytes']


def test_cookie_auth_csrf_and_account_binding(library):
    app, users, clients, _ = library
    assert app.test_client().get(API).status_code == 401
    client, headers = clients[0]
    assert client.post(API, json={'document': document()}).status_code == 401
    csrf_only = {'X-CSRF-TOKEN': headers['X-CSRF-TOKEN']}
    assert client.post(API, json={'document': document()}, headers=csrf_only).json['code'] == 'account_changed'
    wrong_account = {**headers, 'X-Mapmaker-Account': str(users[1].id)}
    assert client.get(API, headers=wrong_account).status_code == 409
    assert client.post(API, json={'document': document()}, headers=wrong_account).status_code == 409
    users[0].is_suspended = True
    db.session.commit()
    assert client.get(API).status_code == 401


def test_quota_failure_preserves_document_and_other_upload_usage(library):
    _, users, clients, _ = library
    client, headers = clients[0]
    project = create(library)
    users[0].storage_used_gb = 1 - 8/GIB
    db.session.commit()
    before = used(users[0])
    larger = document('A much longer project title, with more bytes')
    result = client.put(API + '/' + project['id'], json={'revision': 1, 'document': larger}, headers=headers)
    assert result.status_code == 507
    assert used(users[0]) == before
    assert client.get(API + '/' + project['id']).json['project'] == project
    assert client.post(API, json={'document': document()}, headers=headers).status_code == 507
    users[0].storage_quota_gb = None
    db.session.commit()
    result = client.put(API + '/' + project['id'], json={'revision': 1, 'document': document('A')}, headers=headers)
    assert result.status_code == 200
    size = result.json['project']['sizeBytes']
    assert used(users[0]) == before + size - project['sizeBytes']
    assert client.delete(API + '/' + project['id'], json={'revision': 2}, headers=headers).status_code == 200
    assert used(users[0]) == before - project['sizeBytes']


@pytest.mark.parametrize('tier,platform,quota,allowed', [
    ('player', None, None, False), ('dm', None, 0, False), ('player', None, 1, True),
    ('dm', None, 20, True), ('headmaster', None, None, True), ('player', 'admin', None, True),
])
def test_assigned_storage_policy(library, tier, platform, quota, allowed):
    user = library[1][0]
    user.profile_tier, user.platform_role, user.storage_quota_gb = tier, platform, quota
    db.session.commit()
    client, headers = library[2][0]
    result = client.post(API, json={'document': document()}, headers=headers)
    assert result.status_code == (201 if allowed else 507)
    assert used(user) == (result.json['project']['sizeBytes'] if allowed else 0)


@pytest.mark.parametrize('method', ['put', 'delete'])
def test_stale_revision_does_not_overwrite(library, method):
    project = create(library)
    client, headers = library[2][0]
    path = API + '/' + project['id']
    assert client.put(path, json={'revision': 1, 'document': document('Neu')}, headers=headers).status_code == 200
    result = getattr(client, method)(path, json={'revision': 1, 'document': document('Alt')}, headers=headers)
    assert result.status_code == 409 and result.json['code'] == 'revision_conflict'
    assert client.get(path).json['document']['meta']['title'] == 'Neu'


def test_storage_failure_cleans_partial_upload_and_keeps_previous_version(library, monkeypatch):
    project = create(library)
    client, headers = library[2][0]
    original = LocalStorageAdapter.upload
    def fail(self, key, content):
        original(self, key, content[:40])
        raise OSError('simulated disk failure')
    monkeypatch.setattr(LocalStorageAdapter, 'upload', fail)
    result = client.put(API + '/' + project['id'], json={'revision': 1, 'document': document('New')}, headers=headers)
    assert result.status_code == 503
    assert used(library[1][0]) == project['sizeBytes']
    assert client.get(API + '/' + project['id']).json['project'] == project
    assert len(list(library[3].rglob('*.json'))) == 1


def test_database_commit_failure_cleans_new_object(library, monkeypatch):
    project = create(library)
    client, headers = library[2][0]
    original = db.session.commit
    def fail(): raise RuntimeError('simulated commit failure')
    monkeypatch.setattr(db.session, 'commit', fail)
    assert client.put(API + '/' + project['id'], json={'revision': 1, 'document': document('New')}, headers=headers).status_code == 503
    monkeypatch.setattr(db.session, 'commit', original)
    assert used(library[1][0]) == project['sizeBytes']
    assert client.get(API + '/' + project['id']).json['project'] == project
    assert len(list(library[3].rglob('*.json'))) == 1


@pytest.mark.parametrize('bad', ['external_png', 'dimensions', 'unknown_asset', 'duplicate_id', 'crop', 'too_many_items', 'nan', 'bool_number', 'invalid_png'])
def test_invalid_documents_cannot_consume_storage(library, bad):
    doc = document()
    if bad == 'external_png': doc['layers'][0]['png'] = 'https://example.invalid/private.png'
    if bad == 'dimensions': doc['size']['w'] = 512
    if bad == 'unknown_asset': doc['layers'][1]['items'][0]['asset'] = 'color:missing'
    if bad == 'duplicate_id': doc['layers'][1]['items'][0]['id'] = 'r'
    if bad == 'crop': doc['layers'][1]['items'][0]['crop']['w'] = 65536
    if bad == 'too_many_items': doc['layers'][1]['items'] *= 2001
    if bad == 'nan': doc['layers'][1]['items'][0]['x'] = float('nan')
    if bad == 'bool_number': doc['size']['h'] = True
    if bad == 'invalid_png': doc['layers'][0]['png'] = 'data:image/png;base64,YmFk'
    client, headers = library[2][0]
    response = client.post(API, json={'document': doc}, headers=headers)
    assert response.status_code == 400, response.json
    assert used(library[1][0]) == 0
    assert MapmakerProject.query.count() == 0
    assert not list(library[3].rglob('*.json'))


def test_search_pagination(library):
    client, _ = library[2][0]
    for i in range(26): create(library, document(f'Karte {i}'))
    assert len(client.get(API).json['projects']) == 24
    assert len(client.get(API + '?page=2').json['projects']) == 2
    assert client.get(API + '?q=Karte%2025').json['total'] == 1
    assert client.get(API + '?q=%25').json['total'] == 0
    assert client.get(API + '?page=foo').status_code == 400
    assert len(known_assets()) == 72064


def test_migration_is_additive_and_repeatable(library):
    from tools.migrate_mapmaker_library import migrate
    project = create(library)
    assert migrate(library[0]) == migrate(library[0]) == 'mapmaker_projects ready'
    assert db.session.get(MapmakerProject, project['id']).title == project['title']
