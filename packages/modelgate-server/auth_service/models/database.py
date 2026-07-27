import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'modelgate')}"
    f"?options=-csearch_path%3Dauth_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AuthBase(DeclarativeBase):
    """Tabel milik auth_service."""
    pass


# Fase 5 (ROADMAP.md, BACKLOG.md E3): schema creation is now owned
# entirely by Alembic (`alembic upgrade head`, run before the app starts
# — see Dockerfile), not by an init_db()-on-startup create_all() call.
# Two things can silently drift apart if both exist: a model field added
# without a matching migration would still "work" via create_all() while
# never being tracked by Alembic at all, and self-hosted deployments with
# real data need a migration path, not a dev-only reset-and-recreate.


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
