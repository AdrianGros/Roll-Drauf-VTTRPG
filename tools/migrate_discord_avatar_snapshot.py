"""Add one optional OAuth display snapshot. Run after backup, before the new app.

The preceding app ignores this nullable column; no data backfill is required.
"""
import json
import os

from sqlalchemy import create_engine, inspect, text


def upgrade(connection):
    inspector = inspect(connection)
    if not inspector.has_table('discord_identity_links'):
        raise RuntimeError('Existing Discord identity schema required.')
    columns = {column['name']: column for column in inspector.get_columns('discord_identity_links')}
    if connection.dialect.name == 'postgresql':
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    added = 'avatar_hash' not in columns
    if added:
        connection.execute(text('ALTER TABLE discord_identity_links ADD COLUMN avatar_hash VARCHAR(64)'))
    actual = next(c for c in inspect(connection).get_columns('discord_identity_links') if c['name'] == 'avatar_hash')
    if str(actual['type']).upper() != 'VARCHAR(64)' or not actual['nullable']:
        raise RuntimeError('Unexpected avatar_hash type or nullability; do not activate the app.')
    return {'status': 'pass', 'table': 'discord_identity_links', 'column': 'avatar_hash', 'added': added, 'nullable': True}


if __name__ == '__main__':
    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.begin() as connection:
            result = upgrade(connection)
    finally:
        engine.dispose()
    print(json.dumps(result))
