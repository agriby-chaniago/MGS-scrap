import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'modelgate')}"
    f"?options=-csearch_path%3Danalysis_svc%2Caudit_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AnalysisBase(DeclarativeBase):
    """Tabel milik analysis_service. Ikut create_all()."""
    pass


class AuditWriteBase(DeclarativeBase):
    """Write access ke audit_svc. TIDAK ikut create_all()."""
    pass


# Fase 5 (ROADMAP.md, BACKLOG.md E3): schema creation/evolution is now
# owned entirely by Alembic (`alembic upgrade head`, run in the container
# entrypoint before the app starts), not an init_db()-on-startup
# create_all() call.


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
