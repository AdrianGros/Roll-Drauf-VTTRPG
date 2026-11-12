"""Add only the session calendar and date-poll tables before deploying calendar code.

Run with the target's configured DATABASE_URL: python -m tools.migrate_session_calendar
Only new tables are created (SessionSeries/SessionOccurrence and SessionDatePoll/
Option/Vote). No existing table, column, session or permission is altered; an older
image simply ignores the additional tables. Take a database dump first.
"""
import os

from sqlalchemy import create_engine, inspect, text

from vtt.models import (SessionDateOption, SessionDatePoll, SessionDateVote,
                        SessionOccurrence, SessionSeries)

NEW_TABLES = ('session_series', 'session_occurrences',
              'session_date_polls', 'session_date_options', 'session_date_votes')


def upgrade(connection):
    if connection.dialect.name == 'postgresql':
        connection.execute(text("SELECT pg_advisory_xact_lock(20261005, 1)"))
    if not all(inspect(connection).has_table(name) for name in ('campaigns', 'users', 'game_sessions')):
        raise RuntimeError('Existing VTT schema required before adding calendar tables.')
    # Dependency order; checkfirst keeps repeated runs harmless.
    for model in (SessionSeries, SessionOccurrence, SessionDatePoll, SessionDateOption, SessionDateVote):
        model.__table__.create(connection, checkfirst=True)


if __name__ == '__main__':
    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        with engine.begin() as connection:
            upgrade(connection)
    finally:
        engine.dispose()
    print('Session calendar and date-poll schema ready.')
