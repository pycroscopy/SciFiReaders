from __future__ import division, print_function, unicode_literals, absolute_import
import unittest
import sys

import sidpy

sys.path.append("../SciFiReaders/")
import SciFiReaders
import hyperspy.api as hs
import hyperspy.datasets.artificial_data as ad

class TestHyperspy(unittest.TestCase):
    def test_signal_1d(self):
        s = ad.get_low_loss_eels_signal()
        self.assertTrue(s.metadata.Signal.signal_type == 'EELS')
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)

    def test_signal_2d(self):
        s = ad.get_atomic_resolution_tem_signal2d()
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)

    def test_specrtalImages(self):
        s = ad.get_low_loss_eels_line_scan_signal()
        self.assertTrue(s.metadata.Signal.signal_type == 'EELS')
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)


if __name__ == '__main__':
    unittest.main()
