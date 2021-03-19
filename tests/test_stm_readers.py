import unittest
import sys
sys.path.append("../SciFiReaders/")

class TestNanonisDat(unittest.TestCase):
    #Tests the nanonis_dat reader

    def test_load_test_dat_file(self):
        #Test if the test dat file can be read in correctly
        import SciFiReaders as sr
        import sidpy
        file_path = '../data/Bias-Spectroscopy041.dat'
        data_translator = sr.NanonisDatReader(file_path)
        datasets = data_translator.read(verbose=False)
        assert len(datasets)==24, "Length of dataset should be 24 but is instead {}".format(len(datasets))
        metadata = datasets[0].metadata
        original_metadata ={'Experiment': 'bias spectroscopy',
         'Date': '07.07.2020 15:01:50',
         'User': '',
         'X (m)': 1.10123e-06,
         'Y (m)': 1.89724e-06,
         'Z (m)': 9.92194e-08,
         'Z offset (m)': 0.0,
         'Settling time (s)': 0.0002,
         'Integration time (s)': 0.0006,
         'Z-Ctrl hold': 'TRUE',
         'Final Z (m)': 'N/A',
         'Filter type': 'Gaussian',
         'Order': 2.0,
         'Cutoff frq': ''}

        data_descriptors = ['Current  (A)',
         'Vert. Deflection  (V)',
         'X  (m)',
         'Y  (m)',
         'Z  (m)',
         'Excitation  (V)',
         'Current [bwd]  (A)',
         'Vert. Deflection [bwd]  (V)',
         'X [bwd]  (m)',
         'Y [bwd]  (m)',
         'Z [bwd]  (m)',
         'Excitation [bwd]  (V)',
         'Current  (A)',
         'Vert. Deflection  (V)',
         'X  (m)',
         'Y  (m)',
         'Z  (m)',
         'Excitation  (V)',
         'Current  (A)',
         'Vert. Deflection  (V)',
         'X  (m)',
         'Y  (m)',
         'Z  (m)',
         'Excitation  (V)']

        dim0_values = [datasets[ind].dim_0.values for ind in range(len(datasets))]

        for key in original_metadata:
            assert original_metadata[key] == metadata[key], "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])

        for ind in range(len(datasets)):
            assert type(datasets[ind])== sidpy.sid.dataset.Dataset, "Dataset No. {} not read in as sidpy dataset" \
                    "but was instead read in as {}".format(ind, type(datasets[ind]))

            assert datasets[ind].labels == ['Voltage (V)'], "Dataset {} label should be a ['Voltage (V)'] but " \
                                                      "is instead {}".format(ind,datasets[ind].labels)

            assert datasets[ind].data_descriptor == data_descriptors[ind], "data descriptor " \
                       "for dataset [{}] is {} but should be {}".format(ind, datasets[ind].data_descriptor,data_descriptors[ind])

            assert datasets[ind].shape[0]==256, "Dataset[{}] is of size 256 but was read in as {}".format(ind, datasets[ind].shape[0])
            assert type(datasets[ind]._axes[0]) == sidpy.sid.dimension.Dimension, "Dataset should have dimension type " \
                                           "of sidpy Dimension, but is instead {}".format(type(datasets[ind]._axes))

            assert datasets[ind].dim_0.values.all() == dim0_values[ind].all(), "Dimension 0 for dataset {} did not match!".format(ind)

class TestOmicronAsc(unittest.TestCase):

    def test_load_nanonis(self):
        import SciFiReaders as sr
        print(sr.__version__)
        self.assertTrue(True)
