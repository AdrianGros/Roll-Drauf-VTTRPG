import pytest
from sqlalchemy import create_engine, text

from tools.migrate_discord_avatar_snapshot import upgrade
from vtt.models import DiscordIdentityLink
from tests.test_srd_creator_api import app, client, other  # noqa: F401
from vtt.extensions import db


def test_avatar_snapshot_accepts_only_discord_hashes_and_active_links():
    link=DiscordIdentityLink(discord_user_id='123456789012345678',link_status='linked')
    for value in [None,'https://example.invalid/a.png','../escape','x'*32,{},'0'*65]:
        link.set_avatar_snapshot(value)
        assert link.avatar_hash is None and link.avatar_url() is None
    link.set_avatar_snapshot('a_'+'a'*32)
    assert link.avatar_url()=='https://cdn.discordapp.com/avatars/123456789012345678/a_'+('a'*32)+'.png?size=64'
    link.revoke()
    assert link.avatar_url() is None
    link.link_status='linked';link.revoked_at=None;link.discord_user_id='../other'
    assert link.avatar_url() is None


def test_additive_avatar_migration_is_idempotent_and_preserves_rows():
    engine=create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE discord_identity_links (id INTEGER PRIMARY KEY, discord_user_id VARCHAR(32))'))
        connection.execute(text("INSERT INTO discord_identity_links VALUES (1, '123')"))
        assert upgrade(connection)['added'] is True
        assert upgrade(connection)['added'] is False
        assert connection.execute(text('SELECT id, discord_user_id, avatar_hash FROM discord_identity_links')).one()==(1,'123',None)
    engine.dispose()


def test_avatar_migration_refuses_unexpected_existing_column():
    engine=create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE discord_identity_links (id INTEGER PRIMARY KEY, avatar_hash INTEGER NOT NULL)'))
        with pytest.raises(RuntimeError,match='Unexpected avatar_hash'):
            upgrade(connection)
    engine.dispose()


def test_navigation_returns_only_own_active_avatar(app,client,other):
    with app.app_context():
        link=DiscordIdentityLink(user_id=client.user_id,discord_user_id='123456789012345678',link_status='linked')
        link.set_avatar_snapshot('a'*32);db.session.add(link);db.session.commit()
        own_url=link.avatar_url()
    own=client.get('/api/dashboard/navigation')
    assert own.status_code==200 and own.json['user']['avatar_url']==own_url
    assert other.get('/api/dashboard/navigation').json['user']['avatar_url'] is None
    with app.app_context():
        link=DiscordIdentityLink.query.filter_by(user_id=client.user_id).one();link.revoke();db.session.commit()
    assert client.get('/api/dashboard/navigation').json['user']['avatar_url'] is None
