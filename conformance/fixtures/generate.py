#!/usr/bin/env python3
"""Generates the ad hoc fixture ZIPs used to verify Reader structure
detection in Fase 2 (see ROADMAP.md). Deliberately tiny, synthetic,
committed to git — not the real PetImages demo dataset.

Re-run this script to regenerate the fixtures deterministically:
    python3 conformance/fixtures/generate.py
"""

import io
import os
import zipfile

from PIL import Image

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

# A handful of distinct solid-color images per class — enough for
# corruption/duplicate/balance/structure checks to have real signal.
COLORS = {
    "cat": [(200, 50, 50), (210, 60, 60), (190, 40, 40)],
    "dog": [(50, 50, 200), (60, 60, 210)],
}


def _make_image_bytes(color: tuple[int, int, int], size=(16, 16)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _write_zip(zip_path: str, layout: str) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        for label, colors in COLORS.items():
            for i, color in enumerate(colors):
                data = _make_image_bytes(color)
                filename = f"{i}.jpg"
                if layout == "single-root":
                    arcname = f"pets/{label}/{filename}"
                elif layout == "flat-class":
                    arcname = f"{label}/{filename}"
                elif layout == "split":
                    # only put into train/ for i==0, test/ otherwise —
                    # gives both splits non-trivial content
                    split = "train" if i == 0 else "test"
                    arcname = f"{split}/{label}/{filename}"
                else:
                    raise ValueError(layout)
                zf.writestr(arcname, data)
    print(f"wrote {zip_path}")


def main() -> None:
    _write_zip(os.path.join(FIXTURES_DIR, "adhoc-single-root.zip"), "single-root")
    _write_zip(os.path.join(FIXTURES_DIR, "adhoc-flat-class.zip"), "flat-class")
    _write_zip(os.path.join(FIXTURES_DIR, "adhoc-split.zip"), "split")


if __name__ == "__main__":
    main()
