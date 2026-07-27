"""Resolution — informative only, not a normative Requirement (spec §5.5).

Ported from the pre-MGS analysis_service/analyzers/resolution.py. Unlike
the four MGS-000x checkers, this one does not return a RequirementResult
— there is no defensible threshold to attach a PASS/FAIL verdict to yet
(see spec §5.5 for why). Its output goes into Report.informative instead.
"""

import numpy as np
from PIL import Image

from modelgate._rounding import round4
from modelgate.manifest import Manifest


def compute(manifest: Manifest) -> dict:
    widths: list[int] = []
    heights: list[int] = []

    for sample in manifest.samples:
        try:
            with Image.open(sample.source_path) as img:
                w, h = img.size
            widths.append(w)
            heights.append(h)
        except Exception:
            continue  # corruption is MGS-0002's concern, not this one's

    total = len(widths)
    if total == 0:
        return {"total": 0}

    w_arr = np.array(widths, dtype=np.float64)
    h_arr = np.array(heights, dtype=np.float64)
    median_w, median_h = float(np.median(w_arr)), float(np.median(h_arr))
    std_w, std_h = float(np.std(w_arr)), float(np.std(h_arr))

    in_range = sum(
        1
        for w, h in zip(widths, heights)
        if abs(w - median_w) <= std_w and abs(h - median_h) <= std_h
    )

    return {
        "total": total,
        "median_width": round4(median_w),
        "median_height": round4(median_h),
        "std_width": round4(std_w),
        "std_height": round4(std_h),
        "images_in_normal_range": round4(in_range / total),
    }
