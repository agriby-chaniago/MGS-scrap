#!/usr/bin/env python3
"""Generates every fixture ZIP used by the conformance corpus
(conformance/expected/*.json, conformance/runner.py). Deliberately tiny,
synthetic, committed to git — not the real PetImages demo dataset.

Images are deterministic per-pixel random noise, not flat solid colors.
This matters: MGS-0003's perceptual hash (pHash) is DCT-based and
essentially blind to flat color — two solid-color images of very
different colors can still hash near-identically, since a flat image has
almost no frequency content for the DCT to capture. That made an earlier
version of these fixtures accidentally trigger MGS-0003 FAIL on every
single fixture, including ones meant to test something else entirely.
Random noise gives real structure: same seed -> same image; different
seeds -> ~uncorrelated (Hamming distance far above the default
threshold of 10/64); same seed + a few pixel flips -> a genuine
near-duplicate (Hamming distance well within it). See generate.py's own
git history for the flat-color version this replaced.

Re-run to regenerate all fixtures deterministically:
    python3 conformance/fixtures/generate.py
"""

import io
import os
import random
import zipfile

from PIL import Image

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_SIZE = (32, 32)


def _random_image(seed: int) -> Image.Image:
    rng = random.Random(seed)
    img = Image.new("RGB", IMG_SIZE)
    px = img.load()
    for y in range(IMG_SIZE[1]):
        for x in range(IMG_SIZE[0]):
            px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))
    return img


def _near_duplicate_of(seed: int, flips: int = 3) -> Image.Image:
    """A copy of _random_image(seed) with a handful of pixels perturbed —
    close enough in pHash space to be a genuine near-duplicate."""
    img = _random_image(seed).copy()
    rng = random.Random(seed * 99991)
    px = img.load()
    for _ in range(flips):
        x, y = rng.randrange(IMG_SIZE[0]), rng.randrange(IMG_SIZE[1])
        px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))
    return img


def _jpeg_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _write_zip(name: str, members: dict[str, bytes]) -> None:
    path = os.path.join(FIXTURES_DIR, name)
    with zipfile.ZipFile(path, "w") as zf:
        for arcname, data in members.items():
            zf.writestr(arcname, data)
    print(f"wrote {path}")


def build_layout_variants() -> None:
    """Same logical content (2 classes, 5 distinct-seed images), three
    different raw ZIP layouts — this is what proves Reader structure
    detection (and therefore G5 Manifest equivalence) works identically
    regardless of packaging. See BACKLOG.md A1."""
    seeds = {"cat": [1, 2, 3], "dog": [4, 5]}

    single_root, flat, split = {}, {}, {}
    for label, label_seeds in seeds.items():
        for i, seed in enumerate(label_seeds):
            data = _jpeg_bytes(_random_image(seed))
            filename = f"{i}.jpg"
            single_root[f"pets/{label}/{filename}"] = data
            flat[f"{label}/{filename}"] = data
            s = "train" if i == 0 else "test"
            split[f"{s}/{label}/{filename}"] = data

    _write_zip("adhoc-single-root.zip", single_root)
    _write_zip("adhoc-flat-class.zip", flat)
    _write_zip("adhoc-split.zip", split)

    # Fase 6 (ROADMAP.md): a plain-directory (ImageFolder) fixture, same
    # content as the flat-class ZIP above (same seeds -> same bytes) —
    # proves ImageFolderReader isn't a second, only-lightly-tested Reader
    # bolted on next to ZipReader. Its dataset_hash MUST come out
    # identical to adhoc-flat-class.zip's, since both describe the exact
    # same logical Dataset (spec §2.3 — the hash is Reader-independent).
    imagefolder_dir = os.path.join(FIXTURES_DIR, "imagefolder-equivalent")
    for arcname, data in flat.items():
        dest = os.path.join(imagefolder_dir, arcname)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
    print(f"wrote {imagefolder_dir}/ (directory fixture, {len(flat)} files)")


def build_structure_fixtures() -> None:
    _write_zip(
        "structure-pass.zip",
        {"cat/0.jpg": _jpeg_bytes(_random_image(10)), "dog/0.jpg": _jpeg_bytes(_random_image(20))},
    )
    # MGS-0001 fail: only one label in the whole Dataset.
    _write_zip(
        "structure-fail-single-class.zip",
        {
            "cat/0.jpg": _jpeg_bytes(_random_image(11)),
            "cat/1.jpg": _jpeg_bytes(_random_image(12)),
        },
    )
    # edge: nothing evaluable at all — the direct A2-regression fixture.
    _write_zip("edge-empty.zip", {"readme.txt": b"no images in this dataset"})


def build_integrity_fixtures() -> None:
    _write_zip(
        "integrity-pass.zip",
        {"cat/0.jpg": _jpeg_bytes(_random_image(30)), "dog/0.jpg": _jpeg_bytes(_random_image(31))},
    )
    _write_zip(
        "integrity-fail-corrupted.zip",
        {
            "cat/0.jpg": _jpeg_bytes(_random_image(32)),
            "cat/1.jpg": b"this is not a valid jpeg file at all",
            "dog/0.jpg": _jpeg_bytes(_random_image(33)),
        },
    )


def build_duplicate_fixtures() -> None:
    # pass: every image from an unrelated random seed -> pHash far apart.
    _write_zip(
        "duplicate-pass.zip",
        {
            "cat/0.jpg": _jpeg_bytes(_random_image(40)),
            "cat/1.jpg": _jpeg_bytes(_random_image(41)),
            "dog/0.jpg": _jpeg_bytes(_random_image(42)),
            "dog/1.jpg": _jpeg_bytes(_random_image(43)),
        },
    )
    # fail: cat/1 and dog/1 are near-duplicates of cat/0 and dog/0
    # respectively (a few pixels perturbed) -> 2/4 = 50% duplicate_rate,
    # well above the 3% FAIL threshold.
    _write_zip(
        "duplicate-fail-near-identical.zip",
        {
            "cat/0.jpg": _jpeg_bytes(_random_image(50)),
            "cat/1.jpg": _jpeg_bytes(_near_duplicate_of(50)),
            "dog/0.jpg": _jpeg_bytes(_random_image(51)),
            "dog/1.jpg": _jpeg_bytes(_near_duplicate_of(51)),
        },
    )


def build_balance_fixtures() -> None:
    # pass: equal counts per label -> gini 0.0
    _write_zip(
        "balance-pass.zip",
        {
            "cat/0.jpg": _jpeg_bytes(_random_image(60)),
            "cat/1.jpg": _jpeg_bytes(_random_image(61)),
            "dog/0.jpg": _jpeg_bytes(_random_image(62)),
            "dog/1.jpg": _jpeg_bytes(_random_image(63)),
        },
    )
    # fail: heavily skewed counts (1 vs 19 -> gini 0.45) safely above the
    # 0.4 threshold. (1 vs 9 lands at EXACTLY gini=0.4, which is a PASS
    # under the spec's `> 0.4` FAIL condition — not a bug, but the wrong
    # fixture for demonstrating a clear FAIL, so this uses a wider margin.)
    members = {"cat/0.jpg": _jpeg_bytes(_random_image(70))}
    for i in range(19):
        members[f"dog/{i}.jpg"] = _jpeg_bytes(_random_image(71 + i))
    _write_zip("balance-fail-imbalanced.zip", members)


def main() -> None:
    build_layout_variants()
    build_structure_fixtures()
    build_integrity_fixtures()
    build_duplicate_fixtures()
    build_balance_fixtures()


if __name__ == "__main__":
    main()
