"""modelgate — reference implementation of MGS (Model Gate Specification).

Public API surface (stable once tagged 1.0, see ROADMAP.md Fase 4 / D5.1):
    modelgate.audit, modelgate.read_dataset, modelgate.Manifest,
    modelgate.Report, modelgate.RequirementResult

`read_dataset` was added to the public surface in Fase 5 (ROADMAP.md) —
modelgate-server needs structure-only validation (build a Manifest, check
it parses, without running the full Requirement checks) at dataset
upload time, before an audit is even requested. That's a legitimate
standalone use case beyond `audit()`, not an internal implementation
detail, so it's exported rather than reached into via `modelgate._readers`.

Everything else — modelgate._readers, modelgate._checkers, modelgate._rounding
— is implementation detail and may change without notice between minor
versions until the stability guarantee above is declared.
"""

from modelgate._checkers import get_normative_checkers as _get_normative_checkers
from modelgate._checkers import resolution as _resolution
from modelgate.manifest import Manifest
from modelgate._readers import read_dataset
from modelgate.report import Report, RequirementResult, now_iso8601_utc as _now_iso8601_utc

__version__ = "0.0.0.dev0"

# D5.1 (ROADMAP.md): this is the entire stable public surface. Everything
# imported above with a leading underscore is deliberately kept out of
# `dir(modelgate)`'s non-underscore names, not just out of __all__ — a
# stray `import modelgate; modelgate._get_normative_checkers()` should not
# work by accident just because the function happened to get imported here.
__all__ = ["audit", "read_dataset", "Manifest", "Report", "RequirementResult"]


def audit(path: str, config: dict | None = None) -> Report:
    """Evaluate a Dataset at `path` against MGS-1.0.

    `path` may be a ZIP file or a plain directory (ImageFolder layout) —
    see modelgate._readers for what's supported. `config` overrides
    per-Requirement thresholds (e.g. {"hamming_threshold": 8}); whatever
    value ends up used (override or default) is always recorded in the
    Report (spec §4), never left implicit.
    """
    config = config or {}
    manifest = read_dataset(path)

    requirements: list[RequirementResult] = []
    for checker in _get_normative_checkers():
        requirements.append(checker.check(manifest, config))

    informative = {"resolution": _resolution.compute(manifest)}

    return Report(
        spec_version=manifest.spec_version,
        tool_version=__version__,
        dataset_hash=manifest.dataset_hash,
        generated_at=_now_iso8601_utc(),
        requirements=requirements,
        informative=informative,
    )
