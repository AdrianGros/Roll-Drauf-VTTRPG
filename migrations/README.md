# Database Migrations

This project uses Flask-Migrate (Alembic) for schema evolution.

## Initialize (one-time per environment)

```bash
flask db init
```

## Create a migration

```bash
flask db migrate -m "describe change"
```

## Apply migrations

```bash
flask db upgrade
```

## Downgrade (if needed)

```bash
flask db downgrade
```

## Notes

- Production must use migration commands, not runtime `db.create_all()`.
- Migration execution should run inside deploy pipeline before traffic cutover.

## M71 PostgreSQL vision ID compatibility

The historical `migration_m71_vision_fog_of_war.sql` uses integer primary keys
without a PostgreSQL generator. After a verified database backup, run
`PYTHONPATH=. python tools/migrate_vision_postgres_ids.py` in the application
environment to repair only the three vision/fog IDs. Existing identity/serial
generators and rows are retained. The bounded contract and live verification
are recorded in `docs/plans/FEEDBACK_B07_POSTGRES_REPAIR_2026-11-14.md`.
