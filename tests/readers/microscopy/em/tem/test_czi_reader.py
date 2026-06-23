"""
Test of CZIReader
part of SciFiReaders a pycroscopy package
"""

import sys
import sidpy
import numpy as np
import urllib.error
import urllib.parse
import urllib.request
import os
import unittest

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders

data_path = "https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/main/data/microscopy/em/tem/"


class TestCZI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Download test file once for the entire test class."""
        cls.file_name = 'stains first_1.1.czi'
        if not os.path.exists(cls.file_name):
            try:
                remote_name = urllib.parse.quote(cls.file_name)
                urllib.request.urlretrieve(data_path + remote_name, cls.file_name)
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                raise unittest.SkipTest(
                    f"Test CZI dataset is unavailable from {data_path + remote_name}: {exc}"
                ) from exc

    def test_czi_file(self):
        reader = SciFiReaders.CZIReader(self.file_name)
        datasets = reader.read()

        self.assertEqual(type(datasets), list)
        self.assertGreater(len(datasets), 0)

    def test_data_available(self):
        reader = SciFiReaders.CZIReader(self.file_name)

        self.assertIsInstance(reader, sidpy.Reader)

    def test_read_datasets(self):
        reader = SciFiReaders.CZIReader(self.file_name)
        datasets = reader.read()

        expected_labels_3d = ['channel_axis (index)', 'y_axis (m)', 'x_axis (m)']
        expected_labels_2d = ['y_axis (m)', 'x_axis (m)']

        for ind, dataset in enumerate(datasets):
            self.assertIsInstance(dataset, sidpy.Dataset)

            for axis_idx in range(dataset.ndim):
                self.assertIsInstance(dataset._axes[axis_idx], sidpy.Dimension)

            actual_labels = list(dataset.labels)
            if dataset.ndim == 3:
                self.assertEqual(actual_labels, expected_labels_3d)
            else:
                self.assertEqual(actual_labels, expected_labels_2d)

            self.assertIn('instrument', dataset.metadata)
            self.assertGreater(float(dataset.max()), float(dataset.min()))


if __name__ == '__main__':
    unittest.main()
