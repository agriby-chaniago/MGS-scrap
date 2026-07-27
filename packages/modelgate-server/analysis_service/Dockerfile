FROM python:3.11-slim

WORKDIR /app

# Build context is the repo root (see docker-compose.yml's `context: ../..`
# for this service) so modelgate-core can be installed as a sibling
# package — G4/D2.1 (BACKLOG.md): this is the service that used to have
# its own analyzers/ directory (5 checkers duplicating modelgate-core's
# logic); it now calls modelgate.audit() instead.
COPY packages/modelgate-core /modelgate-core
RUN pip install --no-cache-dir /modelgate-core

COPY packages/modelgate-server/analysis_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/modelgate-server/analysis_service/ .
RUN chmod +x docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]
