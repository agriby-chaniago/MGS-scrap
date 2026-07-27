"""MGS-0002 — Integrity (spec §5.2).

Ported from the pre-MGS analysis_service/analyzers/corruption.py — same
detection method (PIL open + verify), now reading Sample.source_path
from the Manifest instead of walking a filesystem directly.
"""

from PIL import Image

from modelgate._rounding import round4
from modelgate.manifest import Manifest
from modelgate.report import RequirementResult

REQUIREMENT_ID = "MGS-0002"


def check(manifest: Manifest, config: dict) -> RequirementResult:
    total = len(manifest.samples)
    if total == 0:
        # MGS-0000: no samples means nothing was evaluated — never PASS.
        return RequirementResult(
            id=REQUIREMENT_ID, verdict="NOT_EVALUATED", config={}, metrics={}, findings=[]
        )

    findings = []
    for sample in manifest.samples:
        try:
            with Image.open(sample.source_path) as img:
                img.verify()
        except Exception as e:
            findings.append({"uri": sample.uri, "error": str(e)})

    findings.sort(key=lambda f: f["uri"])  # spec §6.3 — byte-wise ordering
    corruption_rate = round4(len(findings) / total)
    # Any corruption fails — see spec §5.2 for why no tolerance threshold exists.
    verdict = "FAIL" if corruption_rate > 0.0 else "PASS"

    return RequirementResult(
        id=REQUIREMENT_ID,
        verdict=verdict,
        config={},
        metrics={"corruption_rate": corruption_rate, "total": total, "corrupted": len(findings)},
        findings=findings,
    )
