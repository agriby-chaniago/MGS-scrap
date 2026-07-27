# Contributing to ModelGate / MGS

Thanks for considering a contribution. A few things worth knowing before
you start, since this project has a somewhat unusual shape (a
specification plus a reference implementation, not just a library).

## What lives where

```
packages/
  modelgate-core/     the reference implementation — Python, this is
                       probably where you want to make changes
  modelgate-server/    hosted microservice deployment, consumes
                       modelgate-core
  modelgate-web/        React frontend
  modelgate-streamlit/   archived UI, not actively maintained
  github-action/         GitHub Action wrapping the CLI
specs/mgs/               the MGS specification itself
conformance/             the corpus that proves conformance (see below)
```

See `ROADMAP.md` for the restructuring plan this repo is mid-way
through, and `BACKLOG.md` for the architectural decisions (section G)
that shape everything else.

## The one rule that matters most

**All audit logic lives in `modelgate-core`. Nothing else — not
`modelgate-server`, not the GitHub Action, not any future interface —
is allowed to implement its own checker.** (G4/D2.1, `BACKLOG.md`.) If
you're fixing a bug in how duplicates are detected, or how class
balance is computed, the fix belongs in `packages/modelgate-core/src/modelgate/_checkers/`,
never in `modelgate-server`.

## Conformance is not optional

Any change to `modelgate-core`'s Reader, Checker, or Report logic has
to still reproduce every fixture in `conformance/expected/*.json`
exactly:

```bash
python3 conformance/runner.py
```

If your change is a deliberate, intentional behavior change (not a
bug fix), that's a spec change — see `specs/mgs/MGS-1.0.md` §8 on
versioning, and open an issue to discuss it before writing code. MGS
1.0 is frozen; changing §5 (Requirements) means MGS 1.1+, not editing
the existing spec document.

If you add a new fixture, freeze its expected output with:

```bash
python3 conformance/runner.py --update
```

— but only after reviewing that the output is actually correct, not
just "whatever the code currently produces." An expected file that
encodes a bug is worse than no fixture at all.

## Adding a new Reader (new dataset format)

This is the extension point the whole Reader/Manifest/Checker split
exists for (D3/D3.1, `BACKLOG.md`). A new Reader:

1. Lives in `packages/modelgate-core/src/modelgate/_readers/`.
2. Produces a `Manifest` matching `specs/mgs/MGS-1.0.md` §2.2 exactly —
   no extra normative fields, though implementation-internal fields
   (like `Sample.source_path`) are fine, see the schema note in the spec.
3. Comes with at least one conformance fixture proving its `dataset_hash`
   matches an equivalent fixture in another format, if one exists (see
   `conformance/fixtures/imagefolder-equivalent/` vs.
   `adhoc-flat-class.zip` for the pattern).

## Development setup

```bash
cd packages/modelgate-core
pip install -e ".[dev]"
```

No Docker needed to work on `modelgate-core` — that's the point of it
being dependency-free. Docker is only needed for `modelgate-server`
work; see its own directory for that.

## Commit messages and PRs

Explain the *why*, not just the *what* — especially for anything
touching threshold values, verdict logic, or the Manifest schema. If
you found something surprising while implementing a change (a
pre-existing bug, a race condition, a spec ambiguity), say so — that
context is what future contributors (and future you) will need.
