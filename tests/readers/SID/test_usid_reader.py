import unittest
import numpy as np
import sys
import os
from pywget import wget
import sidpy

sys.path.insert(0, "../../../../SciFiReaders/")
from SciFiReaders import Usid_reader
from SciFiReaders import EMDReader
from sidpy.sid.dataset import Dataset 

import glob




class TestUSIDReader(unittest.TestCase):
    

    def test_data_available(self):
        wget.download(url=r'https://www.dropbox.com/scl/fi/ggvatabim4zgbcie4yddm/HfOx_-2V_0001.h5?rlkey=rzwdutxnyb0gwu2cw3cmrjst4&dl=1', out='relax_test_data.h5')
        reader = Usid_reader('relax_test_data.h5')
        self.assertIsInstance(reader, sidpy.Reader)

    
    def test_read_ndim_issue(self):
        wget.download(url=r'https://www.dropbox.com/scl/fi/ggvatabim4zgbcie4yddm/HfOx_-2V_0001.h5?rlkey=rzwdutxnyb0gwu2cw3cmrjst4&dl=1', out='relax_test_data.h5')
        reader = Usid_reader('relax_test_data.h5')
        datasets = reader.read()
        assert isinstance(datasets, Dataset)
        h5_files = glob.glob('*.h5')
        for file_name in h5_files:
            os.remove(file_name)
            
    


        
        
if __name__ == '__main__':
    unittest.main()
    
        
        