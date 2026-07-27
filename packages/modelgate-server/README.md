# modelgate-server (archived)

This is the hosted microservice stack (FastAPI services, Postgres,
MinIO, RabbitMQ, Nginx gateway) built during the UAS phase of this
project, then rebuilt in Fase 5 (`ROADMAP.md`) to consume
`modelgate-core` instead of duplicating its logic.

It is **archived, not actively maintained** as of the project's pivot
to a library-first focus. The project's primary product is now
`packages/modelgate-core` — a Python library (`pip install`, `from
modelgate import audit`) plus its CLI (`modelgate check`), aimed at the
notebook/pre-training workflow: check a dataset with MGS before you
train on it, in the same script or notebook, no server required.

This stack is kept, not deleted — it's a real, working reference for
"how would you host this as a multi-user web service," last verified
working end-to-end (see `ROADMAP.md` Fase 5: upload → audit → report,
Alembic migrations, conformance corpus run against it over HTTP,
`docker compose up -d --build`). If it's ever revived:

- `packages/modelgate-web` (the React UI) is also archived and known
  broken against this server's current API shape — see its own README.
- `packages/modelgate-streamlit` is archived similarly.
- The server itself should still work as documented in `ROADMAP.md`
  Fase 5 as of the commit that archived it — it just isn't being kept
  in sync with `modelgate-core` changes going forward.

Nothing here is a dependency of `modelgate-core` — the library works
standalone with zero infrastructure, by design.
