from modelgate.manifest import Manifest
from modelgate._readers.base import Reader
from modelgate._readers.imagefolder_reader import ImageFolderReader
from modelgate._readers.zip_reader import ZipReader

_READERS: list[Reader] = [ZipReader(), ImageFolderReader()]


def read_dataset(path: str) -> Manifest:
    for reader in _READERS:
        if reader.can_read(path):
            return reader.read(path)
    raise ValueError(f"No Reader can handle path: {path}")
