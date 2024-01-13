"""
Test of Hyperspy data converter
part of SciFiReader a pycroscopy package

author: Gerd Duscher, UTK
First Version 11/19/2021
"""

import unittest
import pytest
import numpy as np
import sys
import sidpy

# hyperspy = pytest.importorskip("hyperspy", reason="hyperspy not installed")
"""
try:
    import hyperspy.api as hs
    import hyperspy.datasets.artificial_data as ad
except ModuleNotFoundError:
    hs = None
    ad = None


sys.path.insert(0, "../../../SciFiReaders/")
import SciFiReaders
print(SciFiReaders.__version__)

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

    def test_spectral_images(self):
        s = ad.get_low_loss_eels_line_scan_signal()
        self.assertTrue(s.metadata.Signal.signal_type == 'EELS')
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)

    def test_image_stack(self):
        s = hs.signals.Signal2D(np.ones((3, 5, 4)))
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)

    def test_4d_images(self):
        s = hs.signals.Signal2D(np.ones((3, 2, 5, 4)))
        dataset = SciFiReaders.convert_hyperspy(s)
        self.assertIsInstance(dataset, sidpy.Dataset)


if __name__ == '__main__':
    unittest.main()
"""