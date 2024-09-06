import unittest
import sys
from pywget import wget
import sidpy

sys.path.insert(0, "../../../../SciFiReaders/")
from SciFiReaders import NSIDReader

import glob

class TestNSIDReader(unittest.TestCase):

    def test_nsid_bepfm_file(self):
        wget.download(url=r'https://www.dropbox.com/scl/fi/47o3lqye1zip4nsumc2c8/vpfmm_3.hf5?rlkey=y2jel58n9kkl6h3tt2ogq8pqp&dl=1', out='vpfm_data.h5')
        reader = NSIDReader('vpfm_data.h5')
        self.assertIsInstance(reader, sidpy.Reader)
        data = reader.read()
        assert len(data)==3, "Data should have been length 3 but was instead {}".format(len(data))
        #Check to see if these are sidpy datasets
        for key in data:
            assert type(data[key])==sidpy.sid.dataset.Dataset, "Expected sidpy dataset but received {}".format(type(data[ind]))

        data_keys = list(data.keys())

        assert data[data_keys[0]].shape==(3, 128, 128, 1)
        assert data[data_keys[1]].shape == (128, 128, 61)
        assert data[data_keys[2]].shape == (128,128,5)
        
        assert len(data[data_keys[0]].original_metadata.keys())==285, "Expected 285 keys but received {} for data[0]"
        assert len(data[data_keys[1]].original_metadata.keys())==285, "Expected 285 keys but received {} for data[1]"
        assert len(data[data_keys[2]].original_metadata.keys())==0, "Expected 0 keys but received {} for data[2]"


            
if __name__ == '__main__':
    unittest.main()
    
        
        