"""
Tools to read, data in from TEM files

Submodules
----------

.. autosummary::
    :toctree: _autosummary

    dm_reader
    nion_reader
"""
from .dm_reader import DMReader, DM3Reader
from .nion_reader import NionReader
from .emd_reader import EMDReader
from .edax_reader import EDAXReader
from .mrc_reader import MRCReader

__all__ = ['DMReader', 'DM3Reader', 'NionReader', 'EMDReader', 'EDAXReader', 'MRCReader']

all_readers = [DMReader, DM3Reader, NionReader, EMDReader, EDAXReader, MRCReader]