"""Alembic environment for auth_service.

Fase 5 (ROADMAP.md, BACKLOG.md E3/F future-proofing): schema used to be
created purely via Base.metadata.create_all() + ad hoc `ALTER TABLE IF
EXISTS ... ADD COLUMN IF NOT EXISTS` in models/database.py's init_db().
That's fine for a demo that gets reset constantly; it's not fine for
anyone self-hosting with real data, where an uncoordinated schema change
could silently fail or lose data. From here on, schema changes go
through a migration.

Only this service's OWN schema (auth_svc) is in scope — the
`SERVICE_SCHEMA` filter below stops autogenerate from proposing to drop
tables it merely has read access to in other schemas (not relevant for
auth_service specifically, since its search_path is auth_svc-only, but
kept consistent with the other 3 services' env.py, which do share their
DB connection's search_path with schemas they don't own).
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, os.getcwd())

from models.database import AuthBase  # noqa: E402
from models.orm import ApiKey, User  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = AuthBase.metadata

SERVICE_SCHEMA = "auth_svc"


def _database_url() -> str:
    return (
        f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
        f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_DB', 'modelgate')}"
    )


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == SERVICE_SCHEMA
    if type_ == "table":
        return parent_names.get("schema_name") == SERVICE_SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=SERVICE_SCHEMA,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(
            __import__("sqlalchemy").text(f"CREATE SCHEMA IF NOT EXISTS {SERVICE_SCHEMA}")
        )
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            version_table_schema=SERVICE_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
