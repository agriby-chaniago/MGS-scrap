# modelgate-streamlit (archived)

This is the original Streamlit UI built during the UAS phase of this
project. It is **archived, not actively maintained** — it is kept
runnable as a reference/legacy UI, but new development happens in
`packages/modelgate-web` (the React frontend) and `packages/modelgate-core`
(the CLI/library), per the project's restructuring plan
(`ROADMAP.md`, Fase 1).

It talks to `packages/modelgate-server` over the same HTTP API as the
React frontend — no separate backend of its own.

Run it as part of the full stack:

```bash
cd packages/modelgate-server
docker compose up -d --build streamlit
```
