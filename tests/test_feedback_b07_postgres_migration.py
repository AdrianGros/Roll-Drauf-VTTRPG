"""Run against a disposable PostgreSQL database, never the application database."""
import os
import pytest
from sqlalchemy import create_engine, text
from tools.migrate_vision_postgres_ids import migrate, TABLES


@pytest.fixture
def engine():
    url = os.environ.get("VTT_B07_TEST_POSTGRES")
    if not url:
        pytest.skip("Dedicated disposable PostgreSQL URL required")
    engine = create_engine(url)
    with engine.begin() as c:
        assert c.execute(text("SELECT current_database()")).scalar() == "feedback_b07_test"
        for table in TABLES:
            c.execute(text(f"DROP TABLE IF EXISTS public.{table} CASCADE"))
            c.execute(text(f"CREATE TABLE public.{table}(id integer PRIMARY KEY, payload text)"))
            c.execute(text(f"INSERT INTO public.{table} VALUES (41,'keep exactly')"))
    yield engine
    engine.dispose()


def test_repairs_implicit_insert_and_keeps_rows_and_sequences(engine):
    with pytest.raises(Exception):
        with engine.begin() as c:
            c.execute(text("INSERT INTO scene_lights(payload) VALUES ('fails before repair')"))
    with engine.begin() as c:
        assert all(t["identity_added"] for t in migrate(c)["tables"])
    with engine.begin() as c:
        for table in TABLES:
            assert c.execute(text(f"INSERT INTO {table}(payload) VALUES ('new') RETURNING id")).scalar() == 42
            assert c.execute(text(f"SELECT payload FROM {table} WHERE id=41")).scalar() == "keep exactly"
        assert not any(t["identity_added"] for t in migrate(c)["tables"])
        for table in TABLES:
            assert c.execute(text(f"INSERT INTO {table}(payload) VALUES ('next') RETURNING id")).scalar() == 43


def test_existing_serial_is_retained(engine):
    with engine.begin() as c:
        c.execute(text("CREATE SEQUENCE scene_lights_id_seq START WITH 90 OWNED BY scene_lights.id"))
        c.execute(text("ALTER TABLE scene_lights ALTER COLUMN id SET DEFAULT nextval('scene_lights_id_seq')"))
        result = migrate(c)
        assert result["tables"][0]["identity_added"] is False
        assert c.execute(text("INSERT INTO scene_lights(payload) VALUES ('serial') RETURNING id")).scalar() == 90


def test_unexpected_default_rolls_back_all_changes(engine):
    with engine.begin() as c:
        c.execute(text("ALTER TABLE fog_of_war_state ALTER COLUMN id SET DEFAULT 99"))
    with pytest.raises(RuntimeError, match="Unexpected existing ID default"):
        with engine.begin() as c:
            migrate(c)
    with engine.connect() as c:
        assert c.execute(text("SELECT is_identity FROM information_schema.columns WHERE table_name='scene_lights' AND column_name='id'")).scalar() == 'NO'
        assert c.execute(text("SELECT payload FROM scene_lights WHERE id=41")).scalar() == 'keep exactly'
