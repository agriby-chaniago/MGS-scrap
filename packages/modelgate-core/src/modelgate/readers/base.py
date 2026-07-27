"""Reader protocol.

A Reader is the only part of a conformant implementation permitted to
know anything about raw file layout or archive formats (spec §1). Every
Reader produces a Manifest via the same shared structure-detection logic
in _structure.py — that sharing is what fixes the pre-MGS bug where the
upload-time validator and the storage layer each implemented (and
disagreed on) dataset-layout detection independently.
"""

from typing import Protocol

from modelgate.manifest import Manifest


class Reader(Protocol):
    def can_read(self, path: str) -> bool: ...

    def read(self, path: str) -> Manifest: ...
