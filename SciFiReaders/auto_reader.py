from .readers import all_readers

import os
from pathlib import Path
from warnings import warn
import sidpy


_EXTENSION_READER_MAP = {
    '.bmp': {'imagereader'}, '.jpg': {'imagereader'}, '.jpeg': {'imagereader'},
    '.png': {'imagereader'}, '.tif': {'imagereader'}, '.tiff': {'imagereader'},
    '.czi': {'czireader'},
    '.dm3': {'dmreader', 'dm3reader'}, '.dm4': {'dmreader'},
    '.emd': {'emdreader'},
    '.ibw': {'igoribwreader'},
    '.mrc': {'mrcreader'},
    '.ndata': {'nionreader'},
    '.spe': {'ramanspereader'},
    '.gwy': {'gwyddionreader'},
    # extensions the MCP map was missing; add as needed
    '.asc': {'ascreader'}, '.dat': {'nanonisdatreader'},
    '.3ds': {'nanonis3dsreader'}, '.sxm': {'nanonissxmreader'},
     '.gsf': {'gwyddionreader'},
    '.axz': {'axzreader'}, '.mdt': {'mdtreader'}, '.nid': {'nanosurfnidreader'},
    '.rto': {'brukerreader'}, '.spm': {'brukerafmreader'},
    '.curves': {'wsxm1dreader'}, '.stp': {'wsxm1dreader'}, '.cur': {'wsxm1dreader'},
    '.gsi': {'wsxm3dreader'}, '.mov': {'wsxm3dreader'}, '.mpp': {'wsxm3dreader'},
}

_DEPRECATED = {'dm3reader'}


def _matches_extension(reader_cls, suffix):
    expected = _EXTENSION_READER_MAP.get(suffix, set())
    name, module = reader_cls.__name__.lower(), reader_cls.__module__.lower()
    if name in expected:
        return True
    if 'imagereader' in expected and module.endswith('generic.image'):
        return True
    if 'ramanspereader' in expected and 'spe' in module:
        return True
    return False


def _is_deprecated(reader_cls):
    return reader_cls.__name__.lower() in _DEPRECATED


class AutoReader(sidpy.Reader):
    """Selects the concrete SciFiReaders reader for a file and delegates read() to it."""

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path)
        self.reader_cls, self.matched_readers = self.select(file_path)
        self.reader = self.reader_cls(file_path, *args, **kwargs)

    @staticmethod
    def select(file_path):
        """Return (selected reader class, list of all matching reader classes)."""
        suffix = Path(file_path).suffix.lower()
        matches = []
        for reader_cls in all_readers:
            if _is_deprecated(reader_cls) and any(not _is_deprecated(m) for m in matches):
                continue
            if _matches_extension(reader_cls, suffix):
                matches.append(reader_cls)
                continue
            try:
                readable = reader_cls(file_path).can_read()
            except Exception:          # TypeError from legacy can_read(extension=...), or bad file
                continue
            if readable:
                matches.append(reader_cls)

        if not matches:
            raise TypeError(
                f"No suitable reader for files ending in {suffix or '<no suffix>'}. "
                f"Tried: {', '.join(r.__name__ for r in all_readers)}."
            )

        active = [m for m in matches if not _is_deprecated(m)]
        selected = (active or matches)[-1]
        if len(matches) > 1:
            warn(f"Multiple readers may be able to read this file. Using {selected.__name__}.")
        return selected, matches

    def can_read(self):
        return True

    def read(self, *args, **kwargs):
        return self.reader.read(*args, **kwargs)