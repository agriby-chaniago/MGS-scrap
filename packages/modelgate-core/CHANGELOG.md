# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
`modelgate` (this package) and `MGS` (the spec it implements) version
independently — see `specs/mgs/MGS-1.0.md` §8. Each entry notes which
`spec_version` it targets, since that's what actually determines whether
two Reports are comparable, not the tool's own version number.

## [Unreleased]

Targets: **MGS 1.0**

### Added
- Initial `modelgate-core`: Reader → Manifest → Checker → Report pipeline.
- Readers: ZIP, plain directory (ImageFolder layout). Single shared
  structure-detection algorithm (single-root / flat-class / split) used
  by both — see `_readers/_structure.py`.
- Checkers for all four MGS 1.0 normative Requirements: MGS-0001
  (Structure), MGS-0002 (Integrity), MGS-0003 (Duplicate), MGS-0004
  (Balance). Resolution reported as an informative metric only (spec §5.5).
- `modelgate check <path> [--json] [--spec VERSION]` CLI.
- Conformance corpus (`conformance/`) and CI gate
  (`.github/workflows/conformance.yml`).

### Known limitations
- MGS-0001's "a label with zero samples" FAIL condition is not reachable
  in this implementation yet — `Manifest.labels` is derived only from
  samples that exist; detecting a genuinely empty class folder needs a
  Reader that also enumerates empty directories. See
  `specs/mgs/MGS-1.0.md` §9 and `checkers/structure.py`.
- Only ZIP and plain-directory Datasets are supported. COCO, YOLO, and
  HuggingFace-format readers are deferred past the v1.0 public release —
  see `ROADMAP.md` Fase 6.
- No production PyPI release yet — this package has only been verified
  against TestPyPI (`ROADMAP.md` Fase 4). The real `pip install modelgate`
  happens at Fase 7.
