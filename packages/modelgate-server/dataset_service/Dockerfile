FROM python:3.11-slim

WORKDIR /app

# Build context is the repo root (see docker-compose.yml's `context: ../..`
# for this service) so modelgate-core can be installed as a sibling
# package — G4/D2.1 (BACKLOG.md): the server must not have its own
# dataset-structure-validation logic, it consumes modelgate-core's Reader.
COPY packages/modelgate-core /modelgate-core
RUN pip install --no-cache-dir /modelgate-core

COPY packages/modelgate-server/dataset_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/modelgate-server/dataset_service/ .
RUN chmod +x docker-entrypoint.sh

CMD ["./docker-entrypoint.sh"]
