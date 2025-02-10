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


sys.path.insert(0, "../../../../../SciFiReaders/")
import SciFiReaders
print(SciFiReaders.__version__)

data_path = 'https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/main/data/microscopy/em/tem/'


class TestNionReader(unittest.TestCase):

    def test_load_nion_h5_file(self):
        # Test if the test h5 file can be read in correctly
        file_name = wget.download(data_path + '/NionReader_ImageStack_STO_HAADF.h5')
        reader = SciFiReaders.NionReader(file_name)
        datasets = reader.read()
        dataset = datasets['Channel_000']
        self.assertEqual(dataset.title, '10-Recording of SuperScan (HAADF)')
        self.assertEqual(dataset.source, 'NionReader')
        self.assertEqual(dataset.data_type.name, 'IMAGE_STACK')
        self.assertEqual(float(dataset[1, 200, 200]), 0.3707197606563568)
        self.assertEqual(float(dataset[13, 200, 200]), 0.392993688583374)
        self.assertEqual(float(dataset[17, 200, 200]), 0.4997090995311737)
        self.assertEqual(dataset.shape, (25, 512, 512))
        self.assertEqual(dataset.original_metadata['dimensional_calibrations'][1],
                         {'offset': -4.0, 'scale': 0.015625, 'units': 'nm'})

        os.remove(file_name)

    def test_load_nion_ndata_file(self):
        # Test if the test ndata file can be read in correctly
        file_name = wget.download(data_path + '/NionReader_Image_STO_HAADF.ndata')
        reader = SciFiReaders.NionReader(file_name)
        datasets = reader.read()
        dataset = datasets['Channel_000']
        self.assertEqual(dataset.title, '19-SuperScan (HAADF) 9')
        self.assertEqual(dataset.source, 'NionReader')
        self.assertEqual(dataset.data_type.name, 'IMAGE')

        self.assertEqual(float(dataset[200, 200]), 0.3762475550174713)
        self.assertEqual(float(dataset[100, 200]), 0.35726848244667053)
        self.assertEqual(float(dataset[200, 100]), 0.42469730973243713)
        self.assertEqual(dataset.shape, (1024, 1024))
        self.assertEqual(dataset.original_metadata['dimensional_calibrations'][1],
                         {'offset': -8.0, 'scale': 0.015625, 'units': 'nm'})
        self.assertEqual(dataset.original_metadata['metadata']['hardware_source']['autostem']['high_tension_v'],
                         200000.0)
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
        dataset = datasets['Channel_000']
        self.assertEqual(dataset.data_type.name, 'UNKNOWN')
        os.remove(file_name)
