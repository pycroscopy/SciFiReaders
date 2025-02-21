
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


# Google Drive file ID for a sample .mrc file (replace with actual ID)
MRC_FILE_ID = "1eKRk7nCiSH07z2CetXbBLudbO0pM4V76"
MRC_FILE_PATH = "test_data.mrc"

@pytest.fixture(scope="session")
def download_mrc_file():
    """Download the test MRC file before running tests."""
    if not os.path.exists(MRC_FILE_PATH):
        url = f"https://drive.google.com/uc?id={MRC_FILE_ID}"
        gdown.download(url, MRC_FILE_PATH, quiet=False)
    return MRC_FILE_PATH

def test_read_mrc(download_mrc_file):
    """Test reading an MRC file and checking data consistency."""
    reader = sr.MRCReader(download_mrc_file)
    result = reader.read()
    
    assert "Channel_000" in result, "Output dataset is missing expected channel."
    
    dataset = result["Channel_000"]
    
    assert isinstance(dataset, sidpy.Dataset), "Output is not a sidpy.Dataset instance."
    assert dataset.shape[0] > 0 and dataset.shape[1] > 0, "Spatial dimensions are incorrect."
    
    # assert dataset.data_type == 'image_4d', "Incorrect dataset type."

def test_metadata_extraction(download_mrc_file):
    """Test if metadata is properly extracted."""
    reader = sr.MRCReader(download_mrc_file)
    reader.read()
    
    assert reader.metadata is not None, "Metadata should not be None."
    assert isinstance(reader.metadata, dict), "Metadata should be a dictionary."
    assert len(reader.metadata) > 0, "Metadata dictionary is empty."

def test_data_shape(download_mrc_file):
    """Ensure the data reshaping works as expected."""
    reader = sr.MRCReader(download_mrc_file)
    reader.read()

    assert reader.data is not None, "Data should not be None."
    assert len(reader.data.shape) == 4, "Expected a 4D dataset."