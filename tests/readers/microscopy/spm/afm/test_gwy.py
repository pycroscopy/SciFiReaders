import pytest
import sidpy
import SciFiReaders as sr
from pywget import wget
import os
try:
    import gwyfile
except ImportError:
    import pip
    pip.main(['install', 'gwyfile'])
root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/afm/"

@pytest.fixture
def gwy_file():
    file_path = 'PTO_110_Virgin0001.gwy'
    wget.download(root_path + "/PTO_110_Virgin0001.gwy?raw=true", out=file_path)
    yield file_path
    os.remove(file_path)

def test_load_test_gwy_file(gwy_file):
    data_translator = sr.GwyddionReader(gwy_file)
    datasets = data_translator.read(verbose=False)
    assert len(datasets) == 4, f"Length of dataset should be 2 but is instead {len(datasets)}"
    channel_names = ['HeightRetrace', 'AmplitudeRetrace', 'DeflectionRetrace', 'PhaseRetrace']
    channel_units = ['m', 'm', 'm', 'deg']
    channel_labels = [['x (m)', 'y (m)'], ['x (m)', 'y (m)'], ['x (m)', 'y (m)'], ['x (m)', 'y (m)']]
    for ind, dataset in enumerate(datasets):
        assert isinstance(dataset, sidpy.sid.dataset.Dataset), f"Dataset No. {ind} not read in as sidpy dataset but was instead read in as {type(dataset)}"
        assert dataset.shape[0] == 256, f"Dataset[{ind}] is of size 512 but was read in as {dataset.shape[0]}"
        assert isinstance(dataset._axes[0], sidpy.sid.dimension.Dimension), "Dataset should have dimension type of sidpy Dimension, but is instead {}".format(type(dataset._axes))
        assert dataset.quantity == channel_names[ind], "Dataset having inconsistent channel names"
        assert dataset.units == channel_units[ind], "Dataset having inconsistent unit names"
        assert dataset.labels == channel_labels[ind], "Dataset having inconsistent channel labels"
