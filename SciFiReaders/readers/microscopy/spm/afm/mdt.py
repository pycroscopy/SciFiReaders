

import numpy as np
import sidpy as sid
from sidpy.sid import Reader
from mdt_reader.MDTfile_new import MDTfile


class MDTReader(Reader):
    """
        Extracts data and metadata from NT-MDT (.mdt) binary files containing
        images or curves.

    """

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)

    def read(self, verbose=False):
        pass #TODO

    def can_read(self):
        """
        Tests whether or not the provided file has a .ibw extension
        Returns
        -------

        """

        return super(MDTReader, self).can_read(extension='mdt')
