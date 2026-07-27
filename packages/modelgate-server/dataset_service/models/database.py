import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "modelgate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "modelgate")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "modelgate_secret")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    f"?options=-csearch_path%3Ddataset_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Fase 5 (ROADMAP.md, BACKLOG.md E3): schema creation/evolution is now
# owned entirely by Alembic (`alembic upgrade head`, run in the container
# entrypoint before the app starts — see Dockerfile), not an
# init_db()-on-startup create_all() + ad hoc ALTER TABLE call. The two
# ALTER TABLE statements that used to live here (file_hash, user_id) are
# gone too — those columns are declared directly on the Dataset model
# now, so they're already part of the baseline migration's create_table.


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
