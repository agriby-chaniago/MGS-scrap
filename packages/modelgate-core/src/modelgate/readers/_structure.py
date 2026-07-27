"""Shared class/split structure detection for all filesystem-shaped Readers.

This is the single implementation deciding (label, split) per file. It
replaces two independent, out-of-sync implementations that used to exist
in the pre-MGS codebase — dataset_service/services/validator.py (used at
upload-validation time) and dataset_service/services/minio_service.py
(used at storage time). The latter only ever handled the single-root
case; a flat-class layout (`Cat/`, `Dog/` directly at the root — the
project's own demo ZIP) silently uploaded zero files. Having exactly one
implementation, used by every Reader, is what makes that class of bug
impossible to reintroduce.
"""

from dataclasses import dataclass

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

SPLIT_NAMES = {"train", "test", "valid", "val", "validation", "training", "testing"}


@dataclass(frozen=True)
class StructureEntry:
    """One classified file within a Dataset."""

    original_path: str  # forward-slash path as given by the Reader's source
    label: str
    split: str | None


def is_image_path(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext) for ext in VALID_EXTENSIONS)


def detect_structure(file_paths: list[str]) -> list[StructureEntry]:
    """Classify (label, split) for each file path.

    `file_paths` MUST already be filtered to files only (no directory
    entries) and forward-slash-separated, relative to the Dataset's own
    root — this function has no knowledge of ZIP vs. directory vs. any
    other raw format, by design (§1 of the spec: Readers own format
    knowledge, this helper is format-agnostic).

    Supports the three layouts the pre-MGS validator recognized:
      1. single root wrapper:  root/label/file             (no split)
      2. split under a root:   root/{train,test,...}/label/file
      3. split at top level:   {train,test,...}/label/file  (no common root)
      4. flat classes:         label/file                  (no root, no split)

    Files that don't fit any recognized depth for the layout the Dataset
    as a whole was classified into are silently skipped (matching the
    old scanner's non-recursive `os.listdir` behavior — a stray
    unexpectedly-nested file was never visible to it either).
    """
    if not file_paths:
        return []

    parsed = [p.split("/") for p in file_paths]
    top_dirs = {parts[0] for parts in parsed if len(parts) >= 2}

    if len(top_dirs) == 1:
        root = next(iter(top_dirs))
        children = {parts[1] for parts in parsed if len(parts) >= 3 and parts[0] == root}
        if children and children <= SPLIT_NAMES:
            # root/split/label/file
            return [
                StructureEntry(p, label=parts[2], split=parts[1])
                for parts, p in zip(parsed, file_paths)
                if len(parts) == 4 and parts[0] == root and parts[1] in SPLIT_NAMES
            ]
        # root/label/file
        return [
            StructureEntry(p, label=parts[1], split=None)
            for parts, p in zip(parsed, file_paths)
            if len(parts) == 3 and parts[0] == root
        ]

    if top_dirs and top_dirs <= SPLIT_NAMES:
        # split/label/file, no common root
        return [
            StructureEntry(p, label=parts[1], split=parts[0])
            for parts, p in zip(parsed, file_paths)
            if len(parts) == 3 and parts[0] in SPLIT_NAMES
        ]

    # flat classes: top-level directory names ARE the labels
    return [
        StructureEntry(p, label=parts[0], split=None)
        for parts, p in zip(parsed, file_paths)
        if len(parts) == 2
    ]
