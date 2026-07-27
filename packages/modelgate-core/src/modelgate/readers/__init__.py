from modelgate.manifest import Manifest
from modelgate.readers.base import Reader
from modelgate.readers.imagefolder_reader import ImageFolderReader
from modelgate.readers.zip_reader import ZipReader

_READERS: list[Reader] = [ZipReader(), ImageFolderReader()]


def read_dataset(path: str) -> Manifest:
    for reader in _READERS:
        if reader.can_read(path):
            return reader.read(path)
    raise ValueError(f"No Reader can handle path: {path}")
