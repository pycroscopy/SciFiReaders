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

sys.path.insert(0,"../../../../../../SciFiReaders/")
import SciFiReaders

data_path = 'https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/main/data/microscopy/em/tem/'
import numpy as np

print(SciFiReaders.__version__)

class TestDMReader(unittest.TestCase):

    def test_load_dm3_file(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_EELS_STO.dm3')
        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        print(datasets)
        dataset = datasets['Channel_000']
        self.assertEqual(dataset.title, '01-EELS Acquire_STO')
        self.assertEqual(dataset.source, 'SciFiReaders.DMReader')
        self.assertEqual(dataset[200].compute(), 135727.0)
        self.assertEqual(dataset.energy_loss[200], 400.0)
        self.assertEqual(dataset.original_metadata['DM']['dm_version'], 3)
        self.assertEqual(dataset.original_metadata['ImageTags']
                         ['EELS']['Acquisition']['Exposure (s)'], 2.0)
        self.assertEqual(dataset.data_type.name, 'SPECTRUM')
        os.remove(file_name)

    def test_load_dm4_file(self):
        file_name = wget.download(data_path + '/DMReader_EELS_STO.dm4')
        reader = SciFiReaders.DMReader(file_name, verbose=True)
        datasets = reader.read()
        dataset = datasets['Channel_000']

        self.assertEqual(dataset.title, 'EELS_STO')
        self.assertEqual(dataset.source, 'SciFiReaders.DMReader')
        self.assertEqual(dataset[200].compute(), 135727.0)
        self.assertEqual(dataset.energy_loss[200], 400.0)
        self.assertEqual(dataset.original_metadata['DM']['dm_version'], 4)
        self.assertEqual(dataset.original_metadata['ImageTags']
                         ['EELS']['Acquisition']['Exposure (s)'], 2.0)
        self.assertEqual(dataset.data_type.name, 'SPECTRUM')
        os.remove(file_name)

    def test_load_no_file(self):
        file_path = './EELS_STO.dm'
        with self.assertRaises(FileNotFoundError):
            reader = SciFiReaders.DMReader(file_path)

    def test_load_wrong_file(self):
        # Test behaviour of wrong data file
        file_name = wget.download(data_path + '/NionReader_Image_STO_HAADF.ndata')
        with self.assertRaises(TypeError):
            _ = SciFiReaders.DMReader(file_name)
        os.remove(file_name)

    def test_load_dm3_spectrum_image(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_SpectrumImage_SI-EELS.dm3')

        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        dataset = datasets['Channel_000']

        self.assertEqual(dataset.title, '06-EELS Spectrum Image')
        self.assertEqual(dataset.source, 'SciFiReaders.DMReader')
        self.assertEqual(dataset.data_type.name, 'SPECTRAL_IMAGE')
        self.assertEqual(dataset.shape, (6, 49, 1024))
        self.assertEqual(dataset[0, 3, 200].compute(), 2304.0)
        self.assertEqual(dataset.energy_loss[200], 450.0)
        self.assertEqual(dataset.original_metadata['DM']['dm_version'], 3)
        self.assertEqual(dataset.original_metadata['ImageTags']
                         ['EELS']['Acquisition']['Exposure (s)'], 0.2)

        os.remove(file_name)

    def test_load_dm3_image(self):
        # Test if the test dm3 file can be read in correctly
        file_name = wget.download(data_path + '/DMReader_Image_SI-Survey.dm3')

        reader = SciFiReaders.DMReader(file_name)
        datasets = reader.read()
        dataset = datasets['Channel_000']

        self.assertEqual(dataset.title, '06-SI Survey Image')
        self.assertEqual(dataset.source, 'SciFiReaders.DMReader')
        self.assertEqual(dataset.data_type.name, 'IMAGE')
        self.assertEqual(dataset.shape, (512, 512))

        self.assertEqual(float(dataset[3, 200].compute()), 2940122.0)
        self.assertEqual(dataset.original_metadata['DM']['dm_version'], 3)
        self.assertEqual(dataset.original_metadata['ImageTags']['DigiScan']['Flyback'], 500.0)
        os.remove(file_name)
        