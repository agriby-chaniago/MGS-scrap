"""MGS-0004 — Balance (spec §5.4).

Gini coefficient over per-label sample counts, ported from the pre-MGS
analysis_service/analyzers/distribution.py. Unlike the old analyzer, this
counts actual classified samples from the Manifest (images only) rather
than every filesystem entry in a class directory — a stray non-image
file could previously shift the Gini coefficient; here it simply isn't
a Sample at all (see readers/_structure.py's extension filter).
"""

from modelgate._rounding import round4
from modelgate.manifest import Manifest
from modelgate.report import RequirementResult

REQUIREMENT_ID = "MGS-0004"
DEFAULT_MAX_GINI = 0.4


def _gini(counts: list[int]) -> float:
    n = len(counts)
    if n == 0 or sum(counts) == 0:
        return 0.0
    counts = sorted(counts)
    total = sum(counts)
    return sum((2 * i - n - 1) * c for i, c in enumerate(counts, 1)) / (n * total)


def check(manifest: Manifest, config: dict) -> RequirementResult:
    max_gini = config.get("max_gini", DEFAULT_MAX_GINI)
    used_config = {"max_gini": max_gini}

    # Gini is undefined for fewer than two labels — defer to MGS-0001 (spec §5.4).
    if len(manifest.samples) == 0 or len(manifest.labels) < 2:
        return RequirementResult(
            id=REQUIREMENT_ID,
            verdict="NOT_EVALUATED",
            config=used_config,
            metrics={},
            findings=[],
        )

    counts_per_label: dict[str, int] = {label: 0 for label in manifest.labels}
    for sample in manifest.samples:
        counts_per_label[sample.label] += 1

    gini_coefficient = round4(_gini(list(counts_per_label.values())))
    verdict = "FAIL" if gini_coefficient > max_gini else "PASS"

    return RequirementResult(
        id=REQUIREMENT_ID,
        verdict=verdict,
        config=used_config,
        metrics={
            "gini_coefficient": gini_coefficient,
            "counts_per_label": counts_per_label,
        },
        findings=[],
    )
