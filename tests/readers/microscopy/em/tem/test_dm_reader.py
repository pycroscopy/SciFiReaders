"""
Test of DM3/DM4 Reader of Digital Microscope Suite files
part of SciFiReader a pycroscopy package

author: Gerd Duscher, UTK
First Version 11/19/2021
"""

import unittest
import sys
import os
from pywget import wget

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

data_path = 'https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/reorg/data/microscopy/em/tem/'


class TestDMReader(unittest.TestCase):

    def test_load_dm3_file(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_EELS_STO.dm3')
        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.title[:8], 'DMReader_EELS_STO')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'SPECTRUM')
        os.remove(file_name)

    def test_load_dm4_file(self):
        file_name = wget.download(data_path + '/DMReader_EELS_STO.dm4')
        reader = SciFiReaders.DMReader(file_name, verbose=True)
        datasets = reader.read()
        self.assertEqual(datasets.title[:8], 'DMReader_EELS_STO')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'SPECTRUM')
        os.remove(file_name)

    def test_load_no_file(self):
        file_path = './EELS_STO.dm'
        with self.assertRaises(FileNotFoundError):
            reader = SciFiReaders.DMReader(file_path)

    def test_load_wrong_file(self):
        # Test behaviour of wrong data file
        file_name = wget.download(data_path + '/NionReader_Image_STO_HAADF.ndata')
        with self.assertRaises(TypeError):
            reader = SciFiReaders.DMReader(file_name)
        os.remove(file_name)

    def test_load_dm3_spectrum_image(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_SpectrumImage_SI-EELS.dm3')

        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.title, 'DMReader_SpectrumImage_SI-EELS')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'SPECTRAL_IMAGE')
        self.assertEqual(datasets.shape, (6, 49, 1024))
        os.remove(file_name)

    def test_load_dm3_image(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_Image_SI-Survey.dm3')

        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        self.assertEqual(datasets.title, 'DMReader_Image_SI-Survey')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'IMAGE')
        self.assertEqual(datasets.shape, (512, 512))
        os.remove(file_name)
