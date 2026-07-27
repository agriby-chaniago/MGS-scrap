"""Reads a Dataset packaged as a ZIP archive.

Deliberately permissive: unlike the pre-MGS upload validator, this Reader
does NOT reject a Dataset for having fewer than two classes, or none at
all — that used to be an HTTP 400 at upload time. Under MGS, "does this
Dataset have at least two non-empty classes" is MGS-0001 (Structure), a
Requirement with a real verdict, not a silent Reader-level rejection
(spec §5.1, and the MGS-0000 Fail Closed principle generally).
"""

import os
import shutil
import tempfile
import zipfile

from modelgate.manifest import Manifest, Sample, compute_dataset_hash, sha256_file, SPEC_VERSION
from modelgate._readers._structure import detect_structure, is_image_path


class ZipReader:
    def can_read(self, path: str) -> bool:
        return path.lower().endswith(".zip") and zipfile.is_zipfile(path)

    def read(self, path: str) -> Manifest:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n for n in zf.namelist() if not n.endswith("/") and is_image_path(n)]
            entries = detect_structure(names)

            extract_dir = tempfile.mkdtemp(prefix="modelgate_zip_")
            samples: list[Sample] = []
            for entry in entries:
                filename = entry.original_path.rsplit("/", 1)[-1]
                canonical_uri = (
                    f"{entry.split}/{entry.label}/{filename}"
                    if entry.split
                    else f"{entry.label}/{filename}"
                )
                dest_path = os.path.join(extract_dir, canonical_uri)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with zf.open(entry.original_path) as src, open(dest_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                samples.append(
                    Sample(
                        uri=canonical_uri,
                        label=entry.label,
                        split=entry.split,
                        bytes=os.path.getsize(dest_path),
                        content_hash=sha256_file(dest_path),
                        source_path=dest_path,
                    )
                )

        labels = sorted({s.label for s in samples})
        splits = sorted({s.split for s in samples if s.split is not None})

        return Manifest(
            spec_version=SPEC_VERSION,
            dataset_uri=path,
            dataset_hash=compute_dataset_hash(samples),
            labels=labels,
            splits=splits,
            samples=samples,
        )
