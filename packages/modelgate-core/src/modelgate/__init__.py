"""modelgate — reference implementation of MGS (Model Gate Specification).

Public API surface (stable once tagged 1.0, see ROADMAP.md Fase 4 / D5.1):
    modelgate.audit, modelgate.Manifest, modelgate.Report

Everything else — modelgate.readers, modelgate.checkers, modelgate._rounding
— is implementation detail and may change without notice between minor
versions until that stability guarantee is declared.
"""

from modelgate.checkers import get_normative_checkers
from modelgate.checkers import resolution as _resolution
from modelgate.manifest import Manifest
from modelgate.readers import read_dataset
from modelgate.report import Report, RequirementResult, now_iso8601_utc

__version__ = "0.0.0.dev0"

__all__ = ["audit", "Manifest", "Report", "RequirementResult"]


def audit(path: str, config: dict | None = None) -> Report:
    """Evaluate a Dataset at `path` against MGS-1.0.

    `path` may be a ZIP file or a plain directory (ImageFolder layout) —
    see modelgate.readers for what's supported. `config` overrides
    per-Requirement thresholds (e.g. {"hamming_threshold": 8}); whatever
    value ends up used (override or default) is always recorded in the
    Report (spec §4), never left implicit.
    """
    config = config or {}
    manifest = read_dataset(path)

    requirements: list[RequirementResult] = []
    for checker in get_normative_checkers():
        requirements.append(checker.check(manifest, config))

    informative = {"resolution": _resolution.compute(manifest)}

    return Report(
        spec_version=manifest.spec_version,
        tool_version=__version__,
        dataset_hash=manifest.dataset_hash,
        generated_at=now_iso8601_utc(),
        requirements=requirements,
        informative=informative,
    )
