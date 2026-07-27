"""MGS-0001 — Structure (spec §5.1)."""

from modelgate.manifest import Manifest
from modelgate.report import RequirementResult

REQUIREMENT_ID = "MGS-0001"


def check(manifest: Manifest, config: dict) -> RequirementResult:
    # NOTE: manifest.labels is derived from samples that actually exist
    # (see readers/_structure.py) — a class folder with zero image files
    # never produces a label at all, so it can never appear here "with
    # zero samples" the way the spec's second FAIL condition describes.
    # Detecting that case needs a Reader that also enumerates empty
    # directories, which isn't implemented yet. Tracked as a known gap,
    # not silently assumed away — the first FAIL condition (fewer than
    # two labels) is fully correct as implemented.
    label_count = len(manifest.labels)
    verdict = "FAIL" if label_count < 2 else "PASS"

    return RequirementResult(
        id=REQUIREMENT_ID,
        verdict=verdict,
        config={},
        metrics={"label_count": label_count},
        findings=[],
    )
