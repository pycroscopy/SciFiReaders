import unittest
import sys
from pywget import wget
import os
sys.path.append("../../../../SciFiReaders/")
import SciFiReaders as sr

neutrons_file_path = 'https://www.dropbox.com/scl/fi/ymnajaeqzq4vyb1y6wtpw/REFL_203757_63_reduced_data_new-reduction.txt?rlkey=zpka77tynqkf0sjb9i22hvpq6&dl=1'

class TestBruker(unittest.TestCase):

    def test_load_test_neutrons_file(self):
        # Test if the force curve file can be successfully read
        file_path = 'nr_file.txt'
        wget.download(neutrons_file_path, out=file_path)
        reader = sr.NeutronReflectivity(file_path)
        data_set = reader.read()

        assert data_set.shape == (242,), "Shape of dataset should be 242 but is instead {}".format(data_set.shape)
        #Need to add some assertions for the metadata and the axis dimension stuff
        """
        
        for ind in range(len(datasets)):
            assert type(datasets[ind])== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                    "but was instead read in as {}".format(ind, type(datasets[ind]))

            assert datasets[ind].shape[0]==512, "Dataset[{}] is of size 512 but was read in as {}".format(ind, datasets[ind].shape[0])
            assert type(datasets[ind]._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(datasets[ind]._axes))
        """
        os.remove(file_path)


        




