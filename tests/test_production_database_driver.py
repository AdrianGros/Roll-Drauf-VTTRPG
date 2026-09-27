"""Verify the installed dependencies support the live Compose database URL."""

from sqlalchemy import create_engine


def test_production_postgres_url_loads_installed_driver():
    # No connection is opened. Engine construction still imports the DBAPI,
    # catching dependency drift that SQLite factory tests cannot detect.
    engine = create_engine("postgresql://release:release@db/release")
    try:
        assert engine.dialect.driver == "psycopg2"
    finally:
        engine.dispose()
