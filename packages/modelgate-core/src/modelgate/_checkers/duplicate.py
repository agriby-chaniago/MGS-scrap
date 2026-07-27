"""MGS-0003 — Duplicate (spec §5.3).

Ported from the pre-MGS analysis_service/analyzers/duplicate.py — same
pHash + vectorized Hamming-distance approach, now reading
Sample.source_path from the Manifest. The threshold is no longer a bare
module constant: it is spec §5.3's default, overridable via
config["hamming_threshold"], and the value actually used is always
recorded on the result (spec §4 — reproducibility).
"""

import imagehash
import numpy as np
from PIL import Image

from modelgate._rounding import round4
from modelgate.manifest import Manifest
from modelgate.report import RequirementResult

REQUIREMENT_ID = "MGS-0003"
DEFAULT_HAMMING_THRESHOLD = 10
FAIL_ABOVE_RATE = 0.03


def check(manifest: Manifest, config: dict) -> RequirementResult:
    threshold = config.get("hamming_threshold", DEFAULT_HAMMING_THRESHOLD)
    used_config = {"hamming_threshold": threshold}
    total = len(manifest.samples)

    if total == 0:
        return RequirementResult(
            id=REQUIREMENT_ID, verdict="NOT_EVALUATED", config=used_config, metrics={}, findings=[]
        )

    hashes: list[tuple[str, imagehash.ImageHash]] = []
    for sample in manifest.samples:
        try:
            with Image.open(sample.source_path) as img:
                h = imagehash.phash(img)
            hashes.append((sample.uri, h))
        except Exception:
            continue  # corruption is MGS-0002's concern, not this one's

    n = len(hashes)
    findings = []
    seen_duplicate_uris: set[str] = set()

    if n > 1:
        matrix = np.array([h.hash.flatten() for _, h in hashes], dtype=np.uint8)
        for i in range(n):
            rest = matrix[i + 1 :]
            if len(rest) == 0:
                break
            distances = np.sum(matrix[i] != rest, axis=1)
            for j in np.where(distances <= threshold)[0]:
                j_abs = i + 1 + int(j)
                uri_a, _ = hashes[i]
                uri_b, _ = hashes[j_abs]
                findings.append({"uri_a": uri_a, "uri_b": uri_b, "distance": int(distances[j])})
                seen_duplicate_uris.add(uri_a)
                seen_duplicate_uris.add(uri_b)

    findings.sort(key=lambda f: (f["uri_a"], f["uri_b"]))  # spec §6.3
    duplicate_rate = round4(len(seen_duplicate_uris) / total)
    verdict = "FAIL" if duplicate_rate > FAIL_ABOVE_RATE else "PASS"

    return RequirementResult(
        id=REQUIREMENT_ID,
        verdict=verdict,
        config=used_config,
        metrics={
            "duplicate_rate": duplicate_rate,
            "total": total,
            "duplicate_pairs": len(findings),
        },
        findings=findings,
    )
