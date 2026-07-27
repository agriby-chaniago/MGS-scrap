"""Alembic environment for analysis_service. See auth_service/alembic/env.py
for the full rationale.

This service's DB connection search_path spans analysis_svc (its own)
and audit_svc (write access to a single column — models/orm.py's
AuditStatus, deliberately on a separate AuditWriteBase never included in
target_metadata here, same as its "TIDAK ikut create_all()" comment
already said pre-Fase-5). The `include_name` filter stops autogenerate
from proposing to manage or drop audit_svc's tables just because this
connection can see them.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

sys.path.insert(0, os.getcwd())

from models.database import AnalysisBase  # noqa: E402
from models.orm import AnalysisResult  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = AnalysisBase.metadata

SERVICE_SCHEMA = "analysis_svc"


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
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SERVICE_SCHEMA}"))
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
