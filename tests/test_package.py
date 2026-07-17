from __future__ import division, print_function, unicode_literals, absolute_import
import unittest
import sys
sys.path.append("../SciFiReaders/")


class TestImport(unittest.TestCase):

    def test_basic(self):
        import SciFiReaders as sr
        print(sr.__version__)
        self.assertTrue(True)
