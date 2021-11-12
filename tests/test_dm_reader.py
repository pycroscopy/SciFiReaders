import unittest
import sys
import os
import sidpy

sys.path.append("../SciFiReaders/")
import SciFiReaders

data_path = os.path.join(os.path.dirname(__file__), '../data')


class TestDMReader(unittest.TestCase):

    def test_load_dm3_file(self):
        # Test if the test dm3 file can be read in correctly
        file_path = os.path.join (data_path, 'EELS_STO.dm3')
        reader = SciFiReaders.DMReader(file_path)
        datasets = reader.read()
        self.assertEqual(datasets.title, 'EELS_STO')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'SPECTRUM')

    def test_load_dm4_file(self):
        file_path = os.path.join(data_path, 'EELS_STO.dm4')
        reader = SciFiReaders.DM3Reader(file_path)
        datasets = reader.read()
        self.assertEqual(datasets.title, 'EELS_STO')
        self.assertEqual(datasets.source, 'SciFiReaders.DMReader')
        self.assertEqual(datasets.data_type.name, 'SPECTRUM')

    def test_load_no_file(self):
        file_path = os.path.join(data_path, 'EELS_STO.dm')
        with self.assertRaises(FileNotFoundError):
            reader = SciFiReaders.DMReader(file_path)

    def test_load_wrong_file(self):
        # Test behaviour of wrong data file
        file_path = os.path.join(data_path, 'STO_Image_Stack_(HAADF).h5')
        with self.assertRaises(TypeError):
            reader = SciFiReaders.DMReader(file_path)


class TestNionReader(unittest.TestCase):

    def test_load_nion_h5_file(self):
        # Test if the test h5 file can be read in correctly
        file_path = os.path.join(data_path, 'STO_Image_Stack_(HAADF).h5')
        reader = SciFiReaders.NionReader(file_path)
        datasets = reader.read()
        self.assertEqual(datasets.title, '10-Recording of SuperScan (HAADF)')
        self.assertEqual(datasets.source, 'NionReader')
        self.assertEqual(datasets.data_type.name, 'IMAGE_STACK')

    def test_load_nion_ndata_file(self):
        # Test if the test ndata file can be read in correctly
        file_path = os.path.join(data_path, 'STO_Image_(HAADF).ndata')
        reader = SciFiReaders.NionReader(file_path)
        datasets = reader.read()
        self.assertEqual(datasets.title, '19-SuperScan (HAADF) 9')
        self.assertEqual(datasets.source, 'NionReader')
        self.assertEqual(datasets.data_type.name, 'IMAGE')

    def test_load_no_file(self):
        # Test if the FileNotFoundError is executed
        file_path = os.path.join(data_path, 'EELS_STO.dm')

        with self.assertRaises(FileNotFoundError):
            reader = SciFiReaders.NionReader(file_path)

    def test_load_wrong_file(self):
        # Test behaviour of wrong data file
        file_path = os.path.join(data_path, 'EELS_STO.dm3')
        reader = SciFiReaders.NionReader(file_path)
        datasets = reader.read()
        self.assertEqual(datasets.data_type.name, 'UNKNOWN')