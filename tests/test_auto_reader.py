"""
Tests for the AutoReader dispatcher.

These tests deliberately do NOT check dataset contents -- that is already
covered by the per-reader tests. They check only that AutoReader picks the
right reader for a file and that the delegated read() returns sidpy Datasets.

part of SciFiReader, a pycroscopy package
"""
import os
import sys
import unittest
import urllib.request
import warnings

import sidpy

sys.path.insert(0, "../")
import SciFiReaders

tem_path = ('https://raw.githubusercontent.com/pycroscopy/SciFiDatasets/'
            'main/data/microscopy/em/tem/')
afm_path = ('https://github.com/pycroscopy/SciFiDatasets/'
            'blob/main/data/microscopy/spm/afm/')

# (local file name, url, expected reader class name)
CASES = [
    ('EMDReader_Spectrum_FEI.emd',
     tem_path + 'EMDReader_Spectrum_FEI.emd', 'EMDReader'),
    ('DMReader_EELS_STO.dm3',
     tem_path + 'DMReader_EELS_STO.dm3', 'DMReader'),
    ('DMReader_EELS_STO.dm4',
     tem_path + 'DMReader_EELS_STO.dm4', 'DMReader'),
    ('NionReader_Image_STO_HAADF.ndata',
     tem_path + 'NionReader_Image_STO_HAADF.ndata', 'NionReader'),
    ('NionReader_ImageStack_STO_HAADF.h5',
     tem_path + 'NionReader_ImageStack_STO_HAADF.h5', 'NionReader'),
    ('IgorIBWReader_ForceCurve.ibw',
     afm_path + 'IgorIBWReader_ForceCurve.ibw?raw=true', 'IgorIBWReader'),
    ('PTO_110_Virgin0001.gwy',
     afm_path + 'PTO_110_Virgin0001.gwy?raw=true', 'GwyddionReader'),
    ('vpfm_data.h5',
     'https://www.dropbox.com/scl/fi/47o3lqye1zip4nsumc2c8/vpfmm_3.hf5'
     '?rlkey=y2jel58n9kkl6h3tt2ogq8pqp&dl=1', 'NSIDReader'),
     ('PTO_SS_00.h5',
          'https://www.dropbox.com/scl/fi/r4dcstilxsdg8un2nl7g0/PTO_SS_00.h5'
          '?rlkey=y4gmc0zq1vpvm8hzrigk5quy3&dl=1', 'ARhdf5Reader',
          'ARhdf5Reader.can_read() ends in a bare return -> None'),
]

# Files whose reader cannot currently be selected by AutoReader, with the
# reason. Move them into CASES once the reader is fixed.
KNOWN_GAPS = [
    ('relax_test_data.h5',
     'https://www.dropbox.com/scl/fi/ggvatabim4zgbcie4yddm/HfOx_-2V_0001.h5'
     '?rlkey=rzwdutxnyb0gwu2cw3cmrjst4&dl=1', 'Usid_reader',
     'Usid_reader defines no can_read()'),
]

KNOWN_UNREACHABLE = {'IgorMatrixReader', 'WSxM2DReader',
                     'FSexpReader', 'Usid_reader'}


def _datasets(result):
    """Normalise a reader's return value to a list of sidpy.Dataset objects."""
    if isinstance(result, sidpy.Dataset):
        return [result]
    if isinstance(result, dict):
        return list(result.values())
    return list(result)


class TestAutoReader(unittest.TestCase):
    downloaded_files = set()

    @classmethod
    def download_file(cls, url, file_name):
        if not os.path.exists(file_name):
            urllib.request.urlretrieve(url, file_name)
        cls.downloaded_files.add(file_name)
        return file_name

    @classmethod
    def tearDownClass(cls):
        for file_name in cls.downloaded_files:
            if os.path.exists(file_name):
                os.remove(file_name)

    def test_selects_expected_reader(self):
        for file_name, url, expected in CASES:
            with self.subTest(file=file_name):
                self.download_file(url, file_name)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    selected, matched = SciFiReaders.AutoReader.select(file_name)
                self.assertEqual(selected.__name__, expected)
                self.assertIn(selected, matched)

    def test_reads_datasets(self):
        for file_name, url, expected in CASES:
            with self.subTest(file=file_name):
                self.download_file(url, file_name)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    reader = SciFiReaders.AutoReader(file_name)
                    result = reader.read()
                self.assertEqual(reader.reader_cls.__name__, expected)
                datasets = _datasets(result)
                self.assertGreater(len(datasets), 0)
                for dataset in datasets:
                    self.assertIsInstance(dataset, sidpy.Dataset)

    def test_is_a_sidpy_reader(self):
        file_name, url, _ = CASES[0]
        self.download_file(url, file_name)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            reader = SciFiReaders.AutoReader(file_name)
        self.assertIsInstance(reader, sidpy.Reader)
        self.assertTrue(reader.can_read())

    def test_unknown_extension_raises(self):
        file_name = 'auto_reader_unknown.xyzzy'
        with open(file_name, 'wb') as file_handle:
            file_handle.write(b'not a microscopy file')
        self.downloaded_files.add(file_name)
        with self.assertRaises(TypeError):
            SciFiReaders.AutoReader.select(file_name)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            SciFiReaders.AutoReader('no_such_file_anywhere.emd')

    def test_known_gaps_still_unselectable(self):
        """Documents readers AutoReader cannot reach yet.

        When one of these starts passing, fix the reader, move its entry
        into CASES and delete it here.
        """
        for file_name, url, expected, reason in KNOWN_GAPS:
            with self.subTest(file=file_name, reason=reason):
                self.download_file(url, file_name)
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore')
                        selected, _ = SciFiReaders.AutoReader.select(file_name)
                except TypeError:
                    continue
                self.assertNotEqual(
                    selected.__name__, expected,
                    f'{expected} is now selectable -- move it into CASES')

    def test_every_registered_reader_is_reachable(self):
        """A reader must be in the extension map or define its own can_read()."""
        from SciFiReaders.auto_reader import _EXTENSION_READER_MAP
        from SciFiReaders.readers import all_readers

        mapped = set().union(*_EXTENSION_READER_MAP.values())
        unreachable = {reader_cls.__name__ for reader_cls in all_readers
                       if reader_cls.__name__.lower() not in mapped
                       and 'can_read' not in vars(reader_cls)}
        self.assertEqual(unreachable - KNOWN_UNREACHABLE, set(),
                         'newly unreachable readers')
        self.assertEqual(KNOWN_UNREACHABLE - unreachable, set(),
                         'now reachable -- drop from KNOWN_UNREACHABLE')


if __name__ == '__main__':
    unittest.main()