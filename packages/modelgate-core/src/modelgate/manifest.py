"""The Manifest — normalized, format-independent representation of a Dataset.

Schema matches specs/mgs/MGS-1.0-draft.md §2.2. `Manifest.root` is the
one field NOT part of that schema — see its docstring below.
"""

import hashlib
from dataclasses import dataclass, field

SPEC_VERSION = "1.0"


@dataclass(frozen=True)
class Sample:
    uri: str  # forward-slash path, unique within a Manifest; the sample's identifier
    label: str  # MUST be a member of Manifest.labels
    split: str | None  # MUST be a member of Manifest.splits if non-empty, else None
    bytes: int
    content_hash: str  # sha256 hex of raw file bytes
    # Implementation-internal, deliberately NOT part of the MGS Manifest
    # schema (spec §2.2) or the equivalence check in spec §7 — that check
    # is defined only over the fields above `source_path`. This is an
    # absolute filesystem path to this sample's actual bytes, letting a
    # Checker decode the image (corruption check, perceptual hash, size)
    # without ever knowing whether the original Dataset was a ZIP, a
    # plain directory, or (later) a COCO/YOLO export — the Reader already
    # did that translation. It is inherently machine-local; two
    # conformant implementations evaluating the "identical Manifest" for
    # the same Dataset will have different `source_path` values on disk,
    # which is expected and does not affect conformance.
    source_path: str = field(compare=False)


@dataclass(frozen=True)
class Manifest:
    spec_version: str
    dataset_uri: str
    dataset_hash: str
    labels: list[str]
    splits: list[str]
    samples: list[Sample]


def compute_dataset_hash(samples: list[Sample]) -> str:
    """spec §2.3 — order-independent fingerprint of a Dataset's contents."""
    lines = sorted(f"{s.uri}:{s.content_hash}" for s in samples)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
