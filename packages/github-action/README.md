# github-action (archived)

A composite GitHub Action wrapping `modelgate check` for use in
third-party CI pipelines (someone else's repo automatically checking a
dataset on every push/PR, without installing anything manually).

**Archived, not actively maintained** — the project's focus is
library-first: `packages/modelgate-core` (`pip install`, `from
modelgate import audit`) and its CLI, aimed at a notebook workflow
(check a dataset before training, in the same script). This Action is a
distribution channel to other people's CI, not part of that core
workflow, so it isn't being kept in active development.

The `action.yml` here is a thin wrapper — it just installs `modelgate`
and runs `modelgate check --spec --json`, same as using the CLI
directly. If this is ever revived, it should still work as-is against
whatever the CLI currently does, since it has no logic of its own to
go stale.
