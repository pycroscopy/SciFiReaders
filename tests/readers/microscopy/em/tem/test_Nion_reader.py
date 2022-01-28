"""
Test of Nion Reader of NION Swift files
part of SciFiReader, a pycroscopy package

author: Gerd Duscher, UTK
First Version 11/19/2021
"""

import unittest
import sys
import os
from pywget import wget

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

data_path = 'https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/main/data/microscopy/em/tem/'


class TestNionReader(unittest.TestCase):

    def test_load_nion_h5_file(self):
        # Test if the test h5 file can be read in correctly
        file_name = wget.download(data_path + '/NionReader_ImageStack_STO_HAADF.h5')
        reader = SciFiReaders.NionReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.title, '10-Recording of SuperScan (HAADF)')
        self.assertEqual(datasets.source, 'NionReader')
        self.assertEqual(datasets.data_type.name, 'IMAGE_STACK')
        os.remove(file_name)

    def test_load_nion_ndata_file(self):
        # Test if the test ndata file can be read in correctly
        file_name = wget.download(data_path + '/NionReader_Image_STO_HAADF.ndata')
        reader = SciFiReaders.NionReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.title, '19-SuperScan (HAADF) 9')
        self.assertEqual(datasets.source, 'NionReader')
        self.assertEqual(datasets.data_type.name, 'IMAGE')
        os.remove(file_name)

    def test_load_no_file(self):
        # Test if the FileNotFoundError is executed
        file_path = os.path.join(data_path, 'I_do_not_exist.dm')

        with self.assertRaises(FileNotFoundError):
            reader = SciFiReaders.NionReader(file_path)

    def test_load_wrong_file(self):
        # Test behaviour of wrong data file
        file_name = wget.download(data_path + '/DMReader_Image_SI-Survey.dm3')
        reader = SciFiReaders.NionReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.data_type.name, 'UNKNOWN')
        os.remove(file_name)
