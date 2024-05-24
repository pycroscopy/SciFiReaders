import unittest
import sys
import sidpy
from pywget import wget
import os
sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders as sr
import pytest
import subprocess
import zipfile

perm_link = r"https://github.com/pycroscopy/SciFiDatasets/raw/main/data/microscopy/spm/afm/PEA_BDA_film-1.axz.zip"

# import ssl
# ssl._create_default_https_context = ssl._create_unverified_context

def download_file(url, output_filename):
    subprocess.run(["wget","--continue", "-O", output_filename, url])
def unzip_archive(archive_path, extract_dir):
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

download_file(perm_link, 'PEA_BDA_film.axz.zip')
unzip_archive('PEA_BDA_film.axz.zip', '')
class TestAxzReader(unittest.TestCase):
    def test_axz_file_general(self):
        # Test if the test axz file can be read in correctly
        file_name = 'PEA_BDA_film-1.axz'
        reader = sr.AxzReader(file_name)
        datasets = reader.read(verbose=False)

        self.assertEqual(type(datasets), dict)
        self.assertEqual(len(datasets), 73)
        self.assertEqual(list(datasets.keys())[10], 'Channel_010')

    def test_axz_dataset_image(self):
        file_name = 'PEA_BDA_film-1.axz'
        reader = sr.AxzReader(file_name)
        datasets = reader.read(verbose=False)
        dataset = datasets['Channel_000']

        self.assertEqual(dataset.title, 'Height 1')
        self.assertEqual(dataset[14,12].compute(), 142.01393127441406)
        self.assertEqual(dataset.data_type.name, 'IMAGE')
        self.assertEqual(dataset.dim_0.units, 'um')
        self.assertEqual(dataset.metadata['Value'], 'PrimaryTrace')
        self.assertEqual(dataset.metadata['Position']['X'], '4.1710000038146973')

    def test_axz_dataset_spectrum(self):
        file_name = 'PEA_BDA_film-1.axz'
        reader = sr.AxzReader(file_name)
        datasets = reader.read(verbose=False)
        dataset = datasets['Channel_070']

        self.assertEqual(dataset.title, 'Spectrum 3')
        self.assertEqual(dataset[12].compute(), 19.734291076660156)
        self.assertEqual(dataset.data_type.name, 'SPECTRUM')
        self.assertEqual(dataset.dim_0.units, 'cm-1')
        self.assertEqual(dataset.metadata['DataPoints'], '251')
        self.assertEqual(dataset.metadata['Location']['X'], '6.424')
        self.assertEqual(dataset.metadata['BackgroundID'], '69fc711b-e7b5-438c-a64b-f914dd665754')