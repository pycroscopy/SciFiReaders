import unittest
import urllib.request
import numpy as np
import sys
import os
import urllib
import sidpy

sys.path.insert(0, "../../../../SciFiReaders/")
from SciFiReaders import Usid_reader

import glob


class TestUSIDReader(unittest.TestCase):
    file_name = 'relax_test_data.h5'
    file_url = 'https://www.dropbox.com/scl/fi/ggvatabim4zgbcie4yddm/HfOx_-2V_0001.h5?rlkey=rzwdutxnyb0gwu2cw3cmrjst4&dl=1'

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(cls.file_name):
            urllib.request.urlretrieve(cls.file_url, cls.file_name)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.file_name):
            os.remove(cls.file_name)

    def test_data_available(self):
        reader = Usid_reader(self.file_name)
        self.assertIsInstance(reader, sidpy.Reader)

    def test_read_ndim_issue(self):
        reader = Usid_reader(self.file_name)
        datasets = reader.read()
        reader.close()
    
        assert isinstance(datasets, sidpy.Dataset)
        """
        h5_files = glob.glob('*.h5')
        for file_name in h5_files:
            os.remove(file_name)
        """
if __name__ == '__main__':
    unittest.main()
    
        
        
