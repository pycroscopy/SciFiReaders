import unittest
import sys
import urllib.request
import sidpy
import urllib
import os

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders as sr

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/afm/"


class TestBruker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Download test files once for the entire test class."""
        cls.force_file_path = 'force_bruker.001'
        cls.image_file_path = 'image_bruker.001'

        if not os.path.exists(cls.force_file_path):
            urllib.request.urlretrieve(root_path + "/BrukerReader_ForceCurve_Sapphire_TAP525.001?raw=true",
                                       cls.force_file_path)
        if not os.path.exists(cls.image_file_path):
            urllib.request.urlretrieve(root_path + "/BrukerReader_Image.001?raw=true",
                                       cls.image_file_path)

    @classmethod
    def tearDownClass(cls):
        """Remove downloaded test files after all tests have run."""
        for f in [cls.force_file_path, cls.image_file_path]:
            if os.path.exists(f):
                os.remove(f)

    def test_load_test_bruker_force_file(self):
        data_translator = sr.BrukerAFMReader(self.force_file_path)
        datasets = data_translator.read(verbose=False)

        self.assertEqual(len(datasets), 2,
                         "Length of dataset should be 2 but is instead {}".format(len(datasets)))
        for ind in range(len(datasets)):
            self.assertIsInstance(datasets[ind], sidpy.sid.dataset.Dataset,
                                  "Dataset No. {} not read in as sidpy dataset "
                                  "but was instead read in as {}".format(ind, type(datasets[ind])))
            self.assertEqual(datasets[ind].shape[0], 512,
                             "Dataset[{}] is of size 512 but was read in as {}".format(ind, datasets[ind].shape[0]))
            self.assertIsInstance(datasets[ind]._axes[0], sidpy.sid.dimension.Dimension,
                                  "Dataset should have dimension type of sidpy Dimension, "
                                  "but is instead {}".format(type(datasets[ind]._axes)))

    def test_load_test_bruker_image_file(self):
        data_translator = sr.BrukerAFMReader(self.image_file_path)
        datasets = data_translator.read(verbose=True)

        self.assertEqual(len(datasets), 8,
                         "Length of dataset should be 8 but is instead {}".format(len(datasets)))
        for ind in range(len(datasets)):
            self.assertIsInstance(datasets[ind], sidpy.sid.dataset.Dataset,
                                  "Dataset No. {} not read in as sidpy dataset "
                                  "but was instead read in as {}".format(ind, type(datasets[ind])))
            self.assertEqual(datasets[ind].shape, (512, 512),
                             "Dataset[{}] is of size (512,512) but was read in as {}".format(ind, datasets[ind].shape))
            self.assertIsInstance(datasets[ind]._axes[0], sidpy.sid.dimension.Dimension,
                                  "Dataset should have dimension type of sidpy Dimension, "
                                  "but is instead {}".format(type(datasets[ind]._axes)))


if __name__ == '__main__':
    unittest.main()