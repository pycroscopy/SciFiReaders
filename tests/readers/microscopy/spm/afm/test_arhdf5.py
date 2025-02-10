import pytest
import sidpy
import SciFiReaders as sr
from pywget import wget
import os
import gdown
try:
    import gdown
except ImportError:
    import pip
    pip.main(['install', 'gdown'])

@pytest.fixture
def arhdf5_file():
    file_path = 'PTO_SS_00.h5'
    gdown.download('https://drive.google.com/uc?id=10LpXdpm2tPiGEE_rqKlrIkZhaYkP_YBs', file_path, quiet=False)
    yield file_path
    os.remove(file_path)

def test_load_test_arhdf5_file(arhdf5_file):
    data_translator = sr.ARhdf5Reader(arhdf5_file)
    datasets = data_translator.read(verbose=False)
    test_data = datasets[1:6]
    assert len(test_data) == 5, f"Length of dataset should be 5 but is instead {len(test_data)}"
    channel_names = ['Defl', 'Amp', 'Phase', 'Phas2', 'Freq']
    channel_units = ['m', 'm', 'deg', 'deg', 'Hz']
    channel_labels = [['x (m)', 'y (m)', 'z (s)'], ['x (m)', 'y (m)', 'z (s)'], ['x (m)', 'y (m)', 'z (s)'], ['x (m)', 'y (m)', 'z (s)'], ['x (m)', 'y (m)', 'z (s)']]
    for ind, dataset in enumerate(test_data):
        assert isinstance(dataset, sidpy.sid.dataset.Dataset), f"Dataset No. {ind} not read in as sidpy dataset but was instead read in as {type(dataset)}"
        assert dataset.shape[0] == 64, f"Dataset[{ind}] is of size 64 but was read in as {dataset.shape[0]}"
        assert isinstance(dataset._axes[0], sidpy.sid.dimension.Dimension), "Dataset should have dimension type of sidpy Dimension, but is instead {}".format(type(dataset._axes))
        assert dataset.quantity == channel_names[ind], "Dataset having inconsistent channel names"
        assert dataset.units == channel_units[ind], "Dataset having inconsistent unit names"
        assert dataset.labels == channel_labels[ind], "Dataset having inconsistent channel labels"
