# test_mrc_reader.py
# this is really just a placeholder...
# the files are too big to upload to the repository

import unittest
import sys

sys.path.insert(0, '/Users/austin/Documents/GitHub/SciFiReaders/')
import SciFiReaders 
print(SciFiReaders.__version__)


class TestMRCReader(unittest.TestCase):

    def setUp(self):
        # Use a dummy file path; since we won't actually read a file, it can be anything
        self.file_path = 'dummy.mrc'


if __name__ == '__main__':
    unittest.main()