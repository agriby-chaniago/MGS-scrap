#!/bin/sh
set -e
# Fase 5 (ROADMAP.md, BACKLOG.md E3): migrations run before the app
# starts, every container start — cheap and idempotent on an
# already-migrated DB (alembic upgrade head is a no-op if already at
# head), and this is what actually applies a new migration on deploy.
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8005 --reload
