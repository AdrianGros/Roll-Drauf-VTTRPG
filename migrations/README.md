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
