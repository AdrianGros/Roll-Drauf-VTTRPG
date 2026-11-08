"""Opt-in isolated PostgreSQL proof of quota/revision serialization.

MAPMAKER_TEST_DATABASE_URL must identify a disposable database, never production.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import text
import pytest
from flask_jwt_extended import create_access_token
from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.mapmaker_document import normalize_document
from vtt.models import Role, User
from vtt.models.mapmaker_project import MapmakerProject
from vtt.permissions import try_reserve_storage
from test_mapmaker_library import API, document
GIB = 1024**3


@pytest.fixture
def pg(tmp_path, monkeypatch):
    uri = os.environ.get('MAPMAKER_TEST_DATABASE_URL')
    if not uri: pytest.skip('Dedicated MAPMAKER_TEST_DATABASE_URL not configured')
    assert uri.rsplit('/', 1)[-1] == 'mapmaker_library_test', 'Requires disposable mapmaker_library_test database'
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', uri)
    app = create_app('testing')
    app.config.update(STORAGE_PROVIDER='local', LOCAL_STORAGE_PATH=str(tmp_path))
    with app.app_context():
        db.session.execute(text('DROP SCHEMA public CASCADE'))
        db.session.execute(text('CREATE SCHEMA public'))
        db.session.commit()
        db.create_all()
        role = Role(name='Player')
        db.session.add(role)
        db.session.flush()
        user = User(username='parallel', email='parallel@test.invalid', password_hash='unused', role_id=role.id, storage_quota_gb=1)
        db.session.add(user)
        db.session.commit()
        identity = user.id
        token = create_access_token(identity=str(identity))
    def client():
        instance = app.test_client()
        instance.set_cookie('access_token_cookie', token)
        return instance
    yield app, identity, client
    with app.app_context():
        db.session.remove()
        with db.engine.begin() as connection:
            connection.execute(text('DROP SCHEMA public CASCADE'))
            connection.execute(text('CREATE SCHEMA public'))
        db.engine.dispose()


def concurrent(actions):
    barrier = Barrier(len(actions))
    def run(action):
        barrier.wait(timeout=20)
        return action()
    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(run, actions))


def test_parallel_creates_allow_only_remaining_storage(pg):
    app, identity, client = pg
    doc = document()
    size = len(normalize_document(doc)[1])
    with app.app_context():
        user = db.session.get(User, identity)
        user.storage_used_gb = 1 - (size + 4)/GIB
        db.session.commit()
    def save():
        return client().post(API, json={'document': doc}, headers={'X-Mapmaker-Account': str(identity)}).status_code
    statuses = concurrent([save] * 8)
    assert statuses.count(201) == 1 and statuses.count(507) == 7
    with app.app_context():
        assert MapmakerProject.query.count() == 1
        used = db.session.get(User, identity).storage_used_gb
        assert round(used*GIB) == GIB - 4


def test_map_save_and_existing_asset_reservation_share_quota_lock(pg):
    app, identity, client = pg
    doc = document()
    size = len(normalize_document(doc)[1])
    with app.app_context():
        user = db.session.get(User, identity)
        user.storage_used_gb = 1 - (size + 4)/GIB
        db.session.commit()
    def map_save():
        return client().post(API, json={'document': doc}, headers={'X-Mapmaker-Account': str(identity)}).status_code == 201
    def asset_reserve():
        with app.app_context():
            return try_reserve_storage(db.session.get(User, identity), size)
    assert sum(concurrent([map_save, asset_reserve])) == 1
    with app.app_context(): assert round(db.session.get(User, identity).storage_used_gb*GIB) == GIB - 4


def test_parallel_updates_only_one_revision_wins(pg):
    app, identity, client = pg
    headers = {'X-Mapmaker-Account': str(identity)}
    project = client().post(API, json={'document': document()}, headers=headers).json['project']
    def save(index):
        return lambda: client().put(API+'/'+project['id'], json={'document': document(f'Update {index}'), 'revision': 1}, headers=headers).status_code
    statuses = concurrent([save(i) for i in range(6)])
    assert statuses.count(200) == 1 and statuses.count(409) == 5
    with app.app_context():
        project = MapmakerProject.query.one()
        assert project.revision == 2
        assert round(db.session.get(User, identity).storage_used_gb*GIB) == project.size_bytes
