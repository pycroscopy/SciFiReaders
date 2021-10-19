"""
Utilities for automated ingestion of data and metadata in proprietary file formats
"""

from warnings import warn
from .readers import all_readers


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
    valid_readers = []
    for this_reader in all_readers:
        try:
            t = this_reader(file_path)
        except Exception:
            continue
        try:
            # TODO: This code should be absorbed into the constructor. That can fail anyway
            readable = t.can_read()
        except Exception:
            continue
        if readable:
            valid_readers.append(this_reader)
            # print('{} is a valid reader'.format(this_reader))
            
    final_reader = valid_readers[0]
    if len(valid_readers) == 0:
        raise TypeError(
            "The automatic search for a suitable Reader was unsuccessful")
    elif len(valid_readers) > 1:
        warn("Multiple Reader s may be able to read your file."
             + "The {} will be applied.".format(valid_readers[-1])
             + " Consider specifying 'force_translator'")
        final_reader = valid_readers[-1]
    
    try:
        extracted = final_reader(file_path).read()
    except Exception:
        return None

    return extracted
