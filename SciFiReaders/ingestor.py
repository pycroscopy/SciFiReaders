"""
Utilities for automated ingestion of data and metadata in proprietary file formats
"""

from __future__ import division, unicode_literals, print_function, absolute_import
from warnings import warn
from . import readers

all_translators = readers.all_readers

def ingest(file_path):
    """
    Translates raw data file(s) in proprietary file formats into a h5USID file

    Parameters
    ----------
    file_path : str
        Path to raw data file(s)

    Returns
    -------
    Translated file (output of translator.read())
    """
    valid_translators = []
    for translator in all_translators:
        t = translator(file_path)
        if t.can_read():
            valid_translators.append(translator)
    if len(valid_translators) == 0:
        raise TypeError(
            "The automatic search for a suitable translator was unsuccessful")
    elif len(valid_translators) > 1:
        warn("Multiple translators may be able to read your file."
             + "The {} will be applied.".format(valid_translators[-1])
             + " Consider specifying 'force_translator'")
        translated = valid_translators[-1](file_path).read()
    else:
        translated = valid_translators[0](file_path).read()

    return translated
