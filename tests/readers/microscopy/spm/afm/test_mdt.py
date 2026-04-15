"""
Test of MDTReader
part of SciFiReader a pycroscopy package

author: Boris Slautin
First Version 09/01/2023
"""

import sys
import sidpy
import numpy as np
import urllib
import os
import unittest

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/afm/"


class TestMDT(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Download test file once for the entire test class."""
        file_path = os.path.join(root_path, 'test_mdt.mdt?raw=true')
        cls.file_name = 'test_mdt.mdt'
        if not os.path.exists(cls.file_name):
            urllib.request.urlretrieve(file_path, cls.file_name)

    def test_mdt_file(self):
        reader = SciFiReaders.MDTReader(self.file_name)
        datasets = reader.read()

        self.assertEqual(reader._file_size, 2041471)
        self.assertEqual(reader.nb_frame, 3)

        self.assertEqual(type(datasets), dict)
        self.assertEqual(len(datasets), 3)

    def test_data_available(self):
        reader = SciFiReaders.MDTReader(self.file_name)

        self.assertIsInstance(reader, sidpy.Reader)

    def test_read_image(self):
        reader = SciFiReaders.MDTReader(self.file_name)
        datasets = reader.read()
        image = datasets['001_1F:Iprobe']

        self.assertIsInstance(image, sidpy.Dataset)
        self.assertTrue(image.ndim == 2)

        self.assertEqual(image.title, '1F:Iprobe')
        self.assertTrue(image.data_type.name, 'IMAGE')
        self.assertEqual(image.units, 'nA')
        self.assertEqual(image.quantity, 'Iprobe')

        self.assertEqual(image.metadata['date'], '4/5/2023 11:46:5')

        self.assertEqual(float(image[134, 12]), -0.021743940479999998)
        self.assertEqual(float(image[18, 0]), -0.00267030848)
        self.assertEqual(float(image[206, -5]), -0.02784750272)
        self.assertEqual(image.shape, (256, 256))

        self.assertEqual(len(image.original_metadata['Parameters']), 12)
        self.assertDictEqual(image.original_metadata['Parameters']['Measurement'],
                             {'Scanning': {'Location': {'Location': '0'}, 'Angle': {'Angle': '0'}}})
        self.assertEqual(image.original_metadata['Parameters']['Common']['Probe']['HeadName']['HeadName'],
                         'SF005&AU007NTF')
        self.assertIsInstance(image.x, sidpy.Dimension)
        self.assertEqual(image.y.units, 'um')

    def test_read_point_cloud(self):
        reader = SciFiReaders.MDTReader(self.file_name)
        datasets = reader.read()
        point_cloud = datasets['002_Point_Cloud']
        spectrum = point_cloud['point_1']
        pc = reader.to_point_cloud(point_cloud)

        self.assertIsInstance(point_cloud, dict)
        self.assertIsInstance(pc, sidpy.Dataset)
        self.assertTrue(pc.ndim == 3)
        self.assertTrue(spectrum.ndim == 2)

        self.assertTrue(spectrum.data_type.name, 'SPECTRUM')
        self.assertEqual(pc.units, 'nA')
        self.assertEqual(pc.quantity, 'Iprobe')

        self.assertEqual(pc.metadata['date'], '4/5/2023 11:46:5')
        self.assertEqual(pc.metadata['uuid'], '35225116-2439-4022-807D-7C6A5C86C632')

        self.assertEqual(pc.shape, (25, 1, 3522))
        self.assertEqual(spectrum.shape, (3522, 1))

        self.assertEqual(float(pc[10, 0, 300]), -0.02822897536)
        self.assertEqual(float(pc[2, 0, -3]), -10.22003349824)
        self.assertEqual(float(pc[18, 0, 999]), 0.75760466304)


if __name__ == '__main__':
    unittest.main()
