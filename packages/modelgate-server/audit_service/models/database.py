import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'modelgate')}"
    f"?options=-csearch_path%3Daudit_svc%2Cdataset_svc%2Canalysis_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AuditBase(DeclarativeBase):
    """Tabel milik audit_service. Ikut create_all()."""
    pass


class ReadOnlyBase(DeclarativeBase):
    """Mirror dari service lain. TIDAK ikut create_all()."""
    pass


# Fase 5 (ROADMAP.md, BACKLOG.md E3): schema creation/evolution is now
# owned entirely by Alembic (`alembic upgrade head`, run in the container
# entrypoint before the app starts), not an init_db()-on-startup
# create_all() + ad hoc ALTER TABLE call. `user_id` is declared directly
# on the Audit model now, already part of the baseline migration.


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
