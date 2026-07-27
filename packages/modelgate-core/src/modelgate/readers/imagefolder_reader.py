"""Reads a Dataset already laid out as a plain directory tree.

No extraction/copying needed here (unlike ZipReader) — a sample's bytes
already live at a real path on disk. Uses the same shared
`detect_structure` as ZipReader, so a directory and a ZIP with equivalent
contents produce equivalent Manifests (differing only in `dataset_uri`
and each Sample's implementation-internal `source_path`).
"""

import os

from modelgate.manifest import Manifest, Sample, compute_dataset_hash, sha256_file, SPEC_VERSION
from modelgate.readers._structure import detect_structure, is_image_path


class ImageFolderReader:
    def can_read(self, path: str) -> bool:
        return os.path.isdir(path)

    def read(self, path: str) -> Manifest:
        relative_paths = []
        for dirpath, _dirs, filenames in os.walk(path):
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, path).replace(os.sep, "/")
                if is_image_path(rel):
                    relative_paths.append(rel)

        entries = detect_structure(relative_paths)

        samples: list[Sample] = []
        for entry in entries:
            filename = entry.original_path.rsplit("/", 1)[-1]
            canonical_uri = (
                f"{entry.split}/{entry.label}/{filename}"
                if entry.split
                else f"{entry.label}/{filename}"
            )
            source_path = os.path.join(path, *entry.original_path.split("/"))
            samples.append(
                Sample(
                    uri=canonical_uri,
                    label=entry.label,
                    split=entry.split,
                    bytes=os.path.getsize(source_path),
                    content_hash=sha256_file(source_path),
                    source_path=source_path,
                )
            )

        labels = sorted({s.label for s in samples})
        splits = sorted({s.split for s in samples if s.split is not None})

        return Manifest(
            spec_version=SPEC_VERSION,
            dataset_uri=os.path.abspath(path),
            dataset_hash=compute_dataset_hash(samples),
            labels=labels,
            splits=splits,
            samples=samples,
        )
