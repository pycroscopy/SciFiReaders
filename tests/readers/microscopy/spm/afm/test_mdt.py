"""
Test of  MDTReader
part of SciFiReader a pycroscopy package

author: Boris Slautin
First Version 09/01/2023
"""


import sys
import sidpy
import numpy as np
from pywget import wget
import os
import unittest

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

root_path = os.path.join('https://github.com',
                         'Slautin',
                         'test',
                         'blob',
                         '9e4731fc0d821b2509aba33fb76fefe7d6d2dcd5')


class TestMDT(unittest.TestCase):

    def test_mdt_file(self):
        file_path = os.path.join(root_path, 'example2.mdt?raw=true')
        file_name = wget.download(file_path)

        reader = SciFiReaders.MDTReader(file_name)
        datasets = reader.read()

        self.assertEqual(reader._file_size, 2041471)
        self.assertEqual(reader.nb_frame, 3)

        self.assertEqual(type(datasets), list)
        self.assertEqual(len(datasets), 3)

    def test_data_available(self):
        file_path = os.path.join(root_path, 'example2.mdt?raw=true')
        file_name = wget.download(file_path)

        reader = SciFiReaders.MDTReader(file_name)

        self.assertIsInstance(reader, sidpy.Reader)

    def test_read_image(self):
        file_path = os.path.join(root_path, 'example2.mdt?raw=true')
        file_name = wget.download(file_path)

        reader = SciFiReaders.MDTReader(file_name)
        datasets = reader.read()
        image = datasets[1]

        self.assertIsInstance(image, sidpy.Dataset)
        self.assertTrue(image.ndim == 2)

        self.assertEqual(image.title, '1F:Iprobe')
        self.assertEqual(image.type, '2D IMAGE')
        self.assertTrue(image.data_type.name, 'IMAGE')
        self.assertEqual(image.units, 'nA')
        self.assertEqual(image.quantity, 'Iprobe')


        self.assertEqual(image.metadata['date'], '4/5/2023 11:46:5')

        self.assertEqual(float(image[134,12]), -0.021743940479999998)
        self.assertEqual(float(image[18, 0]), -0.00267030848)
        self.assertEqual(float(image[206,-5]), -0.02784750272)
        self.assertEqual(image.shape, (256, 256))

        self.assertEqual(len(image.original_metadata['Parameters']), 12)
        self.assertDictEqual(image.original_metadata['Parameters']['Measurement'],
                         {'Scanning': {'Location': {'Location': '0'}, 'Angle': {'Angle': '0'}}})
        self.assertEqual(image.original_metadata['Parameters']['Common']['Probe']['HeadName']['HeadName'],
                         'SF005&AU007NTF')
        self.assertIsInstance(image.x, sidpy.Dimension)
        self.assertEqual(image.y.units, 'um')

    def test_read_point_cloud(self):
        file_path = os.path.join(root_path, 'example2.mdt?raw=true')
        file_name = wget.download(file_path)

        reader = SciFiReaders.MDTReader(file_name)
        datasets = reader.read()
        point_cloud = datasets[2]

        self.assertIsInstance(point_cloud, sidpy.Dataset)
        self.assertTrue(point_cloud.ndim == 3)

        self.assertTrue(point_cloud.data_type.name, 'POINT CLOUD')
        self.assertEqual(point_cloud.units, 'nA')
        self.assertEqual(point_cloud.quantity, 'Iprobe')

        self.assertEqual(point_cloud.metadata['date'], '4/5/2023 11:46:5')
        self.assertEqual(point_cloud.metadata['uuid'], '35225116-2439-4022-807D-7C6A5C86C632')

        coord_array7_9 = np.array([[53.68982672, 62.55093176],
                                   [53.68982672, 62.78877978],
                                   [53.68982672, 63.0266278 ]])
        self.assertTrue(np.allclose(point_cloud.metadata['coordinates'][7:10], coord_array7_9, rtol=1e-5, atol=1e-5))

        self.assertEqual(point_cloud.shape, (25, 3, 1174))

        self.assertEqual(float(point_cloud[10,2,300]), -0.0171662688)
        self.assertEqual(float(point_cloud[2, 0, -3]), 48.67438297344)
        self.assertEqual(float(point_cloud[18, 1, 999]), 0.75760466304)

        self.assertIsInstance(point_cloud.BVValue, sidpy.Dimension)
        self.assertEqual(point_cloud.point_number.size, 25)
        self.assertEqual(point_cloud.point_number.dimension_type.name, 'POINT_CLOUD')










