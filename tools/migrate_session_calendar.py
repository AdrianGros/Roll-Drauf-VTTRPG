"""Add only the session calendar tables before deploying calendar code.

Run with the target's configured DATABASE_URL: python -m tools.migrate_session_calendar
No existing tables, sessions, or permissions are altered.
"""
import os

from sqlalchemy import create_engine, inspect, text

from vtt.models import SessionOccurrence, SessionSeries


def upgrade(connection):
    if connection.dialect.name == 'postgresql':
        connection.execute(text("SELECT pg_advisory_xact_lock(20261005, 1)"))
    if not all(inspect(connection).has_table(name) for name in ('campaigns', 'users', 'game_sessions')):
        raise RuntimeError('Existing VTT schema required before adding calendar tables.')
    SessionSeries.__table__.create(connection, checkfirst=True)
    SessionOccurrence.__table__.create(connection, checkfirst=True)


if __name__ == '__main__':
    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.begin() as connection:
            upgrade(connection)
    finally:
        engine.dispose()
    print('Session calendar schema ready.')
