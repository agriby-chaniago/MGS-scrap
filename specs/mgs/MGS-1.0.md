# MGS 1.0 — Model Gate Specification

**Status:** Final (frozen 2026-07-27 — see §9)
**License:** CC BY 4.0 (see `specs/LICENSE`)

## 0. What this is

MGS defines what it means for a computer-vision image dataset to be
*evaluated* for quality, and what an *implementation* of that evaluation
must produce so that two independent implementations — in any language —
arrive at the same verdict for the same dataset.

ModelGate is the reference implementation of MGS. MGS is not owned by
ModelGate; other implementations that satisfy this document are equally
conformant (see §7).

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in
this document are to be interpreted as described in RFC 2119.

---

## 1. Terminology

- **Dataset**: a collection of image files organized into classes, as
  supplied by the user (a ZIP, a directory tree, a COCO/YOLO export, etc.).
- **Reader**: a component that parses a Dataset in some concrete format
  and produces a Manifest (§2). Readers are the *only* part of a
  conformant implementation permitted to know anything about raw file
  layout, archive formats, or annotation formats.
- **Manifest**: the normalized, format-independent representation of a
  Dataset (§2). This is the sole input to every Checker.
- **Checker**: a component that evaluates one Requirement (§5) against a
  Manifest and produces a `RequirementResult` (§4). A Checker MUST NOT
  read the filesystem, network, or archive directly — only the Manifest
  handed to it.
- **Report**: the complete output of an evaluation run (§4): one
  `RequirementResult` per Requirement, plus metadata.
- **Verdict**: one of `PASS`, `FAIL`, `NOT_EVALUATED`, `PARTIAL` (§3).

---

## 2. The Manifest

> This is the single most important artifact in this specification.
> Every conformance guarantee in §7 rests on it.

### 2.1 Principle (MGS-EQ)

**Every MGS implementation MUST evaluate an identical Manifest for an
identical Dataset. Verdict equivalence is defined on the Manifest, not on
the raw Dataset.**

A corollary that implementations MUST observe: any component *between*
the Reader and the Checker — including storage, transport, or caching
layers — MUST preserve every field of the Manifest exactly. A storage
layer that reconstructs a Manifest from what it persisted MUST produce a
byte-for-byte-equivalent Manifest to the one the Reader originally
produced. If it cannot, that storage layer is not conformant, regardless
of what the Checkers do.

### 2.2 Schema

```
Manifest:
  spec_version: string              # e.g. "1.0"
  dataset:
    uri:    string                  # Reader-supplied origin identifier
    sha256: string                  # dataset_hash, see §2.3
  labels: [string]                  # canonical class set, sorted (§6.3)
  splits: [string]                  # e.g. ["train", "test"]; MAY be empty
  samples: [Sample]

Sample:
  uri:          string   # forward-slash path, relative to the Reader's
                          # normalized root — this is also the sample's
                          # identifier; MUST be unique within a Manifest
  label:        string   # MUST be a member of Manifest.labels
  split:        string | null   # MUST be a member of Manifest.splits if
                                  # splits is non-empty, else MUST be null
  bytes:        integer  # raw file size, as read by the Reader
  content_hash: string   # sha256 of the raw file bytes
```

A Reader MUST populate every field. A Reader that cannot determine
`split` for a Dataset with no split structure MUST set it to `null`, not
omit the field.

**Implementation note (added during Fase 2 build — see §9):** a Checker
still needs to obtain a Sample's actual bytes to decode it (corruption
check, perceptual hash, pixel dimensions). An implementation MAY carry
additional fields on its in-memory Manifest/Sample representation for
this purpose (e.g. a resolved local filesystem path per Sample) that are
**not** part of this schema. Such fields MUST NOT be included when
serializing a Manifest for comparison under §7 (conformance) — they are
inherently machine-local (a temp-extraction path, say) and two
conformant implementations evaluating the "identical Manifest" for the
same Dataset are expected to differ on them. Only the fields listed
above are normative.

### 2.3 `dataset.sha256` (the dataset fingerprint)

Computed as:

```
sha256(
  "\n".join(
    f"{sample.uri}:{sample.content_hash}"
    for sample in sorted(manifest.samples, key=lambda s: s.uri)
  )
)
```

This MUST be independent of Reader traversal order — sorting by `uri` is
mandatory before hashing — so that the same Dataset always yields the
same fingerprint regardless of filesystem iteration order, archive entry
order, or which Reader (ZIP vs. directory vs. future format) parsed it.

This fingerprint, not a hash of the raw input file, is what a Report's
`dataset_hash` field (§4) records — a Dataset supplied as a ZIP and the
identical Dataset supplied as an already-extracted directory MUST
fingerprint identically.

---

## 3. Verdict semantics

Every `RequirementResult` carries exactly one of:

| Verdict | Meaning |
|---|---|
| `PASS` | The Requirement's condition was evaluated and held. |
| `FAIL` | The Requirement's condition was evaluated and did not hold. |
| `NOT_EVALUATED` | The Requirement could not be evaluated — missing data, an unsupported Manifest shape, or the Checker was not run at all. |
| `PARTIAL` | The Requirement was evaluated for only part of the Manifest (e.g. one split of several) and the result should not be read as covering the whole Dataset. |

### MGS-0000 — Fail Closed

**The absence of evidence MUST NOT be reported as evidence of passing.**

A conformant implementation MUST NOT emit `PASS` for a Requirement it did
not actually evaluate. If a metric a Requirement depends on is missing,
undefined (e.g. computed over zero samples), or the Checker did not run,
the verdict MUST be `NOT_EVALUATED` — never a default/neutral value that
happens to compute to `PASS`.

This is a direct, deliberate rejection of a defect found in the pre-MGS
ModelGate implementation: a Dataset with zero images produced a health
score of 0.80 (`grade A`) because every missing metric silently defaulted
to a neutral value of `1.0`. Under MGS-0000, the same input MUST produce
`NOT_EVALUATED` for every Requirement.

---

## 4. The Report

```
Report:
  spec_version:  string   # MGS version this Report was evaluated against
  tool_version:  string   # implementation + version that produced it
  dataset_hash:  string   # Manifest.dataset.sha256, see §2.3
  generated_at:  string   # ISO-8601, UTC
  requirements:  [RequirementResult]
  informative:   object   # non-normative metrics, see §6

RequirementResult:
  id:       string   # e.g. "MGS-0001"
  verdict:  Verdict  # see §3
  config:   object   # threshold/parameter values actually used for this
                       # run — MUST be present even when defaults were
                       # used unmodified. This is what makes a Report
                       # reproducible: a reader must never have to guess
                       # what threshold produced a given verdict.
  metrics:  object   # the numeric values the verdict was computed from
  findings: [Finding]   # individual violations; MAY be truncated for very
                          # large result sets — if truncated, findings
                          # MUST carry a sibling "findings_truncated: true"
                          # and "findings_total: <int>" in metrics
```

A Report without `spec_version`, `tool_version`, and `dataset_hash` is
not conformant — these three fields are what let a reader of the Report
(a human, a paper reviewer, or another tool) know exactly what was
checked, by what, and against which exact bytes.

---

## 5. Requirements (MGS 1.0)

MGS 1.0 defines four normative Requirements. A fifth property
(resolution consistency) is defined as informative only (§6) — its
current pass/fail threshold is not yet justified rigorously enough to be
normative; see §5.5.

### MGS-0001 — Structure

**A Dataset MUST contain at least two labels, and every label MUST have
at least one sample.**

- `FAIL` if `len(manifest.labels) < 2`, or any label in `manifest.labels`
  has zero samples.
- `PASS` otherwise.
- Never `NOT_EVALUATED` — this Requirement only needs the Manifest
  itself, which by definition exists if a Report is being produced at all.

### MGS-0002 — Integrity

**No sample in a conformant Dataset MAY be corrupted (unreadable as the
image format its extension declares).**

- `metrics.corruption_rate` = (corrupted samples) / (total samples).
- `FAIL` if `corruption_rate > 0.0` — any corrupted file fails this
  Requirement. Corruption is not a continuous quality signal like
  duplication or balance; it is a binary fact about a file (it is or
  isn't readable), so no tolerance threshold is defined for 1.0. A future
  minor version MAY introduce a configurable tolerance; 1.0 does not.
- `NOT_EVALUATED` if `total samples == 0` (per MGS-0000).

### MGS-0003 — Duplicate

**Near-duplicate samples MUST NOT exceed 3% of the Dataset.**

- Similarity is computed via perceptual hash (pHash, DCT-based, 64-bit /
  8×8). Two samples are a duplicate pair if their Hamming distance is
  `<= 10`.
  - **Why pHash, 64-bit, threshold 10 (not left unspecified):** these
    three choices together are what make MGS-0003 results comparable
    across implementations (§7.3) — a different hash algorithm, a
    different bit-length, or an unstated threshold each independently
    make results incomparable even on the same Dataset. 10/64 bits
    (≈84% similarity) is the conventional starting threshold in
    perceptual-hashing literature for catching recompressed, resized, or
    lightly-edited near-duplicates while avoiding false positives between
    genuinely distinct images of similar subject matter (e.g. two
    different photos of a cat). It is deliberately conservative; a
    stricter project MAY override it via `config.hamming_threshold`, and
    the Report's `config` field MUST record whichever value was used.
- `metrics.duplicate_rate` = (samples in at least one duplicate pair) /
  (total samples).
- `FAIL` if `duplicate_rate > 0.03`.
- `NOT_EVALUATED` if `total samples == 0`.

### MGS-0004 — Balance

**Class imbalance, measured by the Gini coefficient over per-label
sample counts, MUST NOT exceed 0.4.**

- `metrics.gini_coefficient` computed over `{label: count}` for all
  labels in `manifest.labels`.
- `FAIL` if `gini_coefficient > 0.4` — 0.4 is the conventional
  low/moderate–high boundary used for Gini-based inequality measures
  generally (below ~0.2 is considered low inequality, ~0.2–0.4 moderate,
  above 0.4 high). A dataset above this line has at least one label
  heavily under-represented relative to the rest, a well-documented cause
  of biased classifiers.
- `NOT_EVALUATED` if `total samples == 0` or `len(manifest.labels) < 2`
  (Gini is undefined for fewer than two labels — defer to MGS-0001 first).

### 5.5 Resolution — informative, not normative (yet)

Resolution consistency (fraction of samples within ±1σ of the median
width/height) is reported under `Report.informative`, not as a
`RequirementResult`. Unlike §5.2–5.4, no threshold for this metric has a
documented, defensible justification in the current implementation — it
was carried over from the pre-MGS codebase without one. Promoting it to
a normative Requirement is deferred to a future MGS version once a
threshold can be justified the way §5.2–5.4 are.

---

## 6. Numeric semantics

Implementations MUST follow these rules exactly; this section exists
because two implementations can run the same algorithm and still produce
different `Report`s if these are left unstated.

### 6.1 Precision

All ratios, rates, and coefficients MUST be computed in IEEE 754 binary64
(double) precision throughout. Values placed into a `Report` MUST be
rounded to exactly 4 decimal places for output.

### 6.2 Rounding mode

Rounding MUST use **round-half-away-from-zero** (e.g. `0.12345` → `0.1235`).

Implementations MUST NOT use round-half-to-even ("banker's rounding") —
this is Python's `round()` built-in default and MUST be explicitly
overridden (e.g. via `decimal.Decimal` with `ROUND_HALF_UP`, or an
equivalent) when producing `Report` output. This single unstated
difference is enough to make two otherwise-identical implementations
disagree at a boundary value.

### 6.3 Ordering

Any list in a `Report` or `Manifest` that requires a deterministic order
(`labels`, `findings`, duplicate pairs, etc.) MUST be sorted ascending by
byte-wise (ordinal, not locale-aware) comparison of its primary key —
`uri` for samples/findings, the label string itself for `labels`. Ties
(e.g. a duplicate pair) are broken by the secondary `uri` in the same
manner.

### 6.4 Hashing

- Content and dataset hashes: SHA-256, lowercase hex, no prefix.
- Perceptual hash (MGS-0003 only): pHash, 64-bit (8×8 DCT), as specified
  in §5.3.

---

## 7. Conformance

### 7.1 Reference implementation, not sole implementation

ModelGate is the reference implementation of MGS. This document, not
ModelGate's source code, is the authority. Any implementation — in any
language — that satisfies §2 through §6 is a conformant MGS
implementation, whether or not it shares a single line of code with
ModelGate.

### 7.2 The conformance corpus

Conformance is demonstrated, not asserted. The `conformance/` directory
in the ModelGate repository defines a corpus of fixture Datasets with
known-correct `Report` output. An implementation is conformant with a
given MGS version if it reproduces that output exactly (per §6) for
every fixture in the corpus.

### 7.3 The interop contract

The corpus is exercised through a process-level CLI contract, not by
importing implementation internals:

```
<tool> check <fixture-dir> --json
```

An implementation's own internals (Python, Rust, Go, or otherwise) are
irrelevant to conformance; only its behavior at this boundary is. This is
deliberate — it is what allows §7.1's claim to be tested rather than
merely stated.

---

## 8. Versioning

MGS versions independently of any implementation's own version number.
`modelgate` (the tool) version 2.x MAY still implement `MGS 1.0`; the two
numbers are not coupled.

Every `Report` MUST record which `spec_version` it was evaluated against
(§4). An implementation SHOULD expose a way for a caller to pin a
specific `spec_version` explicitly (e.g. `--spec mgs-1.0`) and MUST
refuse to silently evaluate against a different spec version than the one
requested.

Changes to §5 (Requirements) — new Requirements, changed thresholds,
changed verdict conditions — constitute a new MGS version. Editorial
clarifications that do not change any `Report` a conformant
implementation would produce do not.

---

## 9. Status

**MGS 1.0 is frozen.** It was carried as a draft through Fase 1–2 of the
ModelGate restructuring (`ROADMAP.md`), revised by findings made while
building the reference implementation's Reader/Manifest/Checker
pipeline, and frozen in Fase 3 once the conformance corpus (§7.2) —
`conformance/fixtures/` + `conformance/expected/*.json`, run via
`conformance/runner.py` — went green across all fixtures. Per §8, further
changes to §5 (Requirements) now constitute MGS 1.1 or later, not edits
to this document.

**Revisions made while it was still a draft (Fase 2 implementation):**
- §2.2 gained the implementation-note paragraph on Sample-level
  filesystem access (`source_path`-style fields) after building the
  actual Reader/Checker split revealed Checkers need a way to read
  bytes, not just metadata, without that becoming part of the
  normative, compared schema.
- §5.1 (MGS-0001 Structure)'s "any label with zero samples" FAIL
  condition is currently unreachable in the reference implementation —
  `Manifest.labels` is derived from samples that exist, so a Reader
  never produces a label with a zero count in the first place. Detecting
  a genuinely empty class folder needs a Reader that also enumerates
  empty directories, not just files, which is not yet implemented.
  Tracked as a known gap in the reference implementation, not a spec
  change — the requirement text in §5.1 is still correct; the FAIL
  condition is honest about what's covered. **This gap survives the
  freeze** — it is a reference-implementation limitation, not something
  §5.1's normative text needs to accommodate.
