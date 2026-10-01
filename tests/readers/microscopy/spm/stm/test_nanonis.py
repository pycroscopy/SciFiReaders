import unittest
import sys
import os
import numpy as np
import sidpy
import pytest
import urllib.request

sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders as sr
from SciFiReaders.readers.microscopy.spm.stm.nanonis_base import Scan

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/stm/"

# test datasets are looked up in <repo>/data/ and downloaded there only if missing
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), *[os.pardir] * 5, 'data'))


def get_test_file(url, file_name):
    """Return the path of file_name in DATA_DIR, downloading it from url first if it is not there."""
    file_path = os.path.join(DATA_DIR, file_name)
    if not os.path.exists(file_path):
        os.makedirs(DATA_DIR, exist_ok=True)
        # download to a temporary name first so an interrupted download never leaves a partial file
        tmp_path = file_path + '.part'
        urllib.request.urlretrieve(url, tmp_path)
        os.replace(tmp_path, file_path)
    return file_path


class TestNanonisDat(unittest.TestCase):
    # Tests the nanonis_dat reader

    def test_load_test_dat_file(self):
        # Test if the test dat file can be read in correctly
        file_path = get_test_file(root_path + "NanonisReader_BiasSpectroscopy.dat?raw=true",
                                  'NanonisReader_BiasSpectroscopy.dat')
        datasets = sr.NanonisDatReader(file_path).read(verbose=False)

        # keys are the column names without the unit; filtered columns carry the unit before their tags
        channels = ['Current', 'Vert. Deflection', 'X', 'Y', 'Z', 'Excitation']
        units = ['A', 'V', 'm', 'm', 'm', 'V']
        expected = {}
        for tags, direction in [('', 'forward'), (' [bwd]', 'backward'),
                                (' [filt]', 'forward'), (' [bwd] [filt]', 'backward')]:
            for name, unit in zip(channels, units):
                expected[name + tags] = (name + tags.replace(' [bwd]', ''), unit, direction)
        assert list(datasets) == list(expected), "Dataset keys should be {} but are {}".format(
            list(expected), list(datasets))

        header = {'Experiment': 'bias spectroscopy',
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

        bias = datasets['Current']._axes[0].values
        assert len(bias) == 256 and bias[0] == -2.0 and bias[-1] == 2.0, "Unexpected bias axis {}".format(bias)

        for key, (name, unit, direction) in expected.items():
            dset = datasets[key]
            assert type(dset) == sidpy.sid.dataset.Dataset, "Dataset {} not read in as sidpy dataset " \
                "but was instead read in as {}".format(key, type(dset))
            assert dset.title == key, "Title of {} is {}".format(key, dset.title)
            assert dset.data_type == sidpy.DataType.SPECTRUM, "Data type of {} is {}".format(key, dset.data_type)
            assert dset.shape == (256,), "Dataset {} should have shape (256,) but has {}".format(key, dset.shape)
            assert dset.quantity == name and dset.units == unit, \
                "Dataset {}: quantity/units {}/{} should be {}/{}".format(key, dset.quantity, dset.units, name, unit)

            dim = dset._axes[0]
            assert type(dim) == sidpy.sid.dimension.Dimension, "Dataset should have dimension type " \
                "of sidpy Dimension, but is instead {}".format(type(dim))
            assert dim.name == 'Bias calc' and dim.units == 'V', \
                "Spectral dimension of {} is {} ({})".format(key, dim.name, dim.units)
            assert np.array_equal(dim.values, bias), "Dimension 0 for dataset {} did not match!".format(key)

            metadata = dset.original_metadata
            ramp = 'increasing' if direction == 'forward' else 'decreasing'
            assert metadata['Name'] == name and metadata['Unit'] == unit, "Name/Unit metadata of {}".format(key)
            assert metadata['Direction'] == direction and metadata['sweep_ramp'] == ramp, \
                "Dataset {}: Direction/sweep_ramp {}/{} should be {}/{}".format(
                    key, metadata['Direction'], metadata['sweep_ramp'], direction, ramp)
            for hkey in header:
                assert header[hkey] == metadata[hkey], "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(hkey, header[hkey], metadata[hkey])

        assert datasets['Current [bwd] [filt]'].original_metadata['Channel'] == 'Current (A) [bwd] [filt]'


class TestNanonisSXM(unittest.TestCase):

    def test_load_nanonis_sxm(self):
        file_path = get_test_file(r'https://www.dropbox.com/s/ozsdm1q83ik8gt8/NanonisReader_COOx_sample2286.sxm?raw=true',
                                  'NanonisReader_COOx_sample2286.sxm')
        datasets = sr.NanonisSXMReader(file_path).read()
        raw = Scan(file_path).signals

        names = ['Z', 'Vert._Deflection', 'Horiz._Deflection', 'Amplitude2', 'Phase_2',
                 'Bias', 'Current', 'Phase', 'Amplitude', 'Frequency_Shift']
        units = ['m', 'V', 'V', 'V', 'V', 'V', 'A', 'deg', 'm', 'Hz']
        expected_keys = [name + ' ' + direction for name in names for direction in ['forward', 'backward']]
        assert list(datasets) == expected_keys, "Dataset keys should be {} but are {}".format(
            expected_keys, list(datasets))

        for name, unit in zip(names, units):
            for direction in ['forward', 'backward']:
                key = name + ' ' + direction
                dset = datasets[key]
                assert type(dset) == sidpy.sid.dataset.Dataset, "Type of dataset expected " \
                    "is sidpy.Dataset, received {}".format(type(dset))
                assert dset.shape == (256, 256), "Shape of dataset should be (256,256) but instead is {}".format(dset.shape)
                assert dset.title == key and dset.quantity == name and dset.units == unit, \
                    "Dataset {}: title/quantity/units {}/{}/{}".format(key, dset.title, dset.quantity, dset.units)
                assert dset.original_metadata['Direction'] == direction

                # scan direction 'up': no vertical flip; backward rows are flipped left-right
                expected = raw[name][direction]
                if direction == 'backward':
                    expected = expected[:, ::-1]
                assert np.array_equal(np.asarray(dset), expected, equal_nan=True), \
                    "Data of {} does not match the file".format(key)

        # axis 0 is Y (rows), axis 1 is X (columns); pitch = scan range / pixels, starting at 0
        dset = datasets['Z forward']
        for ind, name in enumerate(['Y', 'X']):
            dim = dset._axes[ind]
            assert dim.name == name and dim.units == 'nm', "Axis {} is {} ({})".format(ind, dim.name, dim.units)
            assert np.allclose(dim.values, np.arange(256) * 250 / 256), "Axis {} values {}".format(ind, dim.values)

        metadata = dset.original_metadata
        original_metadata = {'Channel': '14',
        'Name': 'Z',
        'Unit': 'm',
        'Direction': 'forward',
        'Calibration': -1.26e-07,
        'Offset': 0.0,
        'nanonis_version': '2',
        'scanit_type': 'FLOAT            MSBFIRST',
        'rec_date': '09.07.2020',
        'rec_time': '13:16:37',
        'rec_temp': '290.0000000000',
        'acq_time': 616.1,
        'scan_pixels': np.array([256, 256]),
        'scan_file': 'C:\\Users\\Administrator\\Documents\\Users\\Kevin Pachuta\\063020\\COOx_sample2286.sxm',
        'scan_time': np.array([1.203, 1.203]),
        'scan_range': np.array([2.5e-07, 2.5e-07]),
        'scan_offset': np.array([1.182551e-06, 1.858742e-06]),
        'scan_angle': 90.0,
        'scan_dir': 'up',
        'bias': 0.0,
        'z-controller': {'Name': ('cAFM',),
        'on': ('1',),
        'Setpoint': ('2.000E+0 V',),
        'P-gain': ('5.167E-9 m/V',),
        'I-gain': ('3.059E-5 m/V/s',),
        'T-const': ('1.689E-4 s',)},
        'comment': 'New sample from Kevin CoOx nanosheets\n',
        'nanonismain>session path': 'C:\\Users\\Administrator\\Documents\\Users\\Kevin Pachuta\\063020',
        'nanonismain>sw version': 'Generic 4',
        'nanonismain>ui release': '8181',
        'nanonismain>rt release': '7685',
        'nanonismain>rt frequency (hz)': '10E+3',
        'nanonismain>signals oversampling': '10',
        'nanonismain>animations period (s)': '20E-3',
        'nanonismain>indicators period (s)': '300E-3',
        'nanonismain>measurements period (s)': '500E-3',
        'bias>bias (v)': '0E+0',
        'bias>calibration (v/v)': '1E+0',
        'bias>offset (v)': '0E+0',
        'current>current (a)': '-185.299E-15',
        'current>calibration (a/v)': '999.99900E-12',
        'current>offset (a)': '-353.221E-15',
        'current>gain': 'High',
        'piezo calibration>active calib.': 'Default',
        'piezo calibration>calib. x (m/v)': '15E-9',
        'piezo calibration>calib. y (m/v)': '15E-9',
        'piezo calibration>calib. z (m/v)': '-9E-9',
        'piezo calibration>hv gain x': '14',
        'piezo calibration>hv gain y': '14',
        'piezo calibration>hv gain z': '14',
        'piezo calibration>tilt x (deg)': '0',
        'piezo calibration>tilt y (deg)': '0',
        'piezo calibration>curvature radius x (m)': 'Inf',
        'piezo calibration>curvature radius y (m)': 'Inf',
        'piezo calibration>2nd order corr x (v/m^2)': '0E+0',
        'piezo calibration>2nd order corr y (v/m^2)': '0E+0',
        'piezo calibration>drift x (m/s)': '0E+0',
        'piezo calibration>drift y (m/s)': '0E+0',
        'piezo calibration>drift z (m/s)': '0E+0',
        'piezo calibration>drift correction status (on/off)': 'FALSE',
        'z-controller>z (m)': '109.389E-9',
        'z-controller>controller name': 'cAFM',
        'z-controller>controller status': 'ON',
        'z-controller>setpoint': '2E+0',
        'z-controller>setpoint unit': 'V',
        'z-controller>p gain': '5.16746E-9',
        'z-controller>i gain': '30.5931E-6',
        'z-controller>time const (s)': '168.909E-6',
        'z-controller>tiplift (m)': '0E+0',
        'z-controller>switch off delay (s)': '0E+0',
        'scan>scanfield': '1.18255E-6;1.85874E-6;250E-9;250E-9;90E+0',
        'scan>series name': 'COOx_sample2',
        'scan>channels': 'Current (A);Vert. Deflection (V);Horiz. Deflection (V);Amplitude2 (V);Phase 2 (V);Bias (V);Z (m);Phase (deg);Amplitude (m);Frequency Shift (Hz)',
        'scan>pixels/line': '256',
        'scan>lines': '256',
        'scan>speed forw. (m/s)': '207.779E-9',
        'scan>speed backw. (m/s)': '207.779E-9'}

        for key in original_metadata:
            if type(original_metadata[key]) == np.ndarray:
                assert np.allclose(original_metadata[key], metadata[key]), "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])
            else:
                assert original_metadata[key] == metadata[key], "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])


class TestNanonis3ds(unittest.TestCase):

    def test_load_nanonis_3ds(self):
        file_path = get_test_file(root_path + "NanonisReader_STS_grid_lockin.3ds?raw=true",
                                  'NanonisReader_STS_grid_lockin.3ds')
        datasets = sr.Nanonis3dsReader(file_path).read()

        channels = {'Current': 'A', 'LockinX': 'V', 'LockinY': 'V', 'Bias_m': 'V'}
        assert list(datasets) == list(channels) + ['Topography'], \
            "Dataset keys should be {} but are {}".format(list(channels) + ['Topography'], list(datasets))

        for key, unit in channels.items():
            dset = datasets[key]
            assert type(dset) == sidpy.sid.dataset.Dataset, "Type of dataset expected " \
                "is sidpy.Dataset, received {}".format(type(dset))
            assert dset.shape == (30, 30, 200), "Shape of dataset should be (30,30,200) but instead is {}".format(dset.shape)
            assert dset.title == key and dset.quantity == key and dset.units == unit, \
                "Dataset {}: title/quantity/units {}/{}/{}".format(key, dset.title, dset.quantity, dset.units)
            assert dset.data_type == sidpy.DataType.SPECTRAL_IMAGE

        # axes: Y (rows), X (columns) in nm with pitch = frame size / pixels; bias sweep
        dset = datasets['Current']
        for ind, name in enumerate(['Y', 'X']):
            dim = dset._axes[ind]
            assert dim.name == name and dim.units == 'nm', "Axis {} is {} ({})".format(ind, dim.name, dim.units)
            assert np.allclose(dim.values, np.arange(30) * 5 / 30), "Axis {} values {}".format(ind, dim.values)
        bias = dset._axes[2]
        assert bias.name == 'Bias' and bias.units == 'V' and len(bias) == 200
        assert np.isclose(bias.values[0], -0.22) and np.isclose(bias.values[-1], 0.22)

        topo = datasets['Topography']
        assert topo.shape == (30, 30) and topo.units == 'm' and topo.data_type == sidpy.DataType.IMAGE

        metadata = dset.original_metadata
        original_metadata = {'Name': 'Current',
        'Direction': 'forward',
        'sweep_ramp': 'increasing',
        'Unit': 'A',
        'Channel': 'Current (A)',
        'dim_px': [30, 30],
        'pos_xy': [8.451877e-08, 6.329924e-07],
        'size_xy': [5e-09, 5e-09],
        'angle': 45.0,
        'sweep_signal': 'Bias (V)',
        'num_parameters': 10,
        'experiment_size': 3200,
        'num_sweep_signal': 200,
        'num_channels': 4,
        'experiment_name': 'Experiment',
        # this file has no Delay / Start time / End time / Comment entries: fall-back values
        'start_time': '',
        'end_time': '',
        'user': '',
        'comment': '',
        'Date': '04.06.2016 20:13:23'}

        for key in original_metadata:
            assert original_metadata[key] == metadata[key], "Metadata incorrect for key {}, should be {} " \
                "but was read as {}".format(key, original_metadata[key], metadata[key])
        assert np.isnan(metadata['measure_delay']), "measure_delay should be nan (not in file)"
        assert np.isclose(metadata['Sweep Start'], -0.22) and np.isclose(metadata['Sweep End'], 0.22)


# one example file per Nanonis reader: (url, local file name, reader class)
AUTO_DETECT_FILES = [(root_path + "NanonisReader_BiasSpectroscopy.dat?raw=true",
                      'NanonisReader_BiasSpectroscopy.dat', sr.NanonisDatReader),
                     (r'https://www.dropbox.com/s/ozsdm1q83ik8gt8/NanonisReader_COOx_sample2286.sxm?raw=true',
                      'NanonisReader_COOx_sample2286.sxm', sr.NanonisSXMReader),
                     (root_path + "NanonisReader_STS_grid_lockin.3ds?raw=true",
                      'NanonisReader_STS_grid_lockin.3ds', sr.Nanonis3dsReader)]


def assert_same_output(result, expected, label):
    assert isinstance(result, dict) and list(result) == list(expected), \
        "{}: keys {} should be {}".format(label, list(result) if isinstance(result, dict) else result, list(expected))
    for key in expected:
        assert np.array_equal(np.asarray(result[key]), np.asarray(expected[key]), equal_nan=True), \
            "{}: data of {} differs".format(label, key)


class TestNanonisAutoDetect(unittest.TestCase):
    # sr.AutoReader must pick the Nanonis reader from the file extension

    def test_autoreader_selects_nanonis_readers(self):
        for url, file_name, reader in AUTO_DETECT_FILES:
            file_path = get_test_file(url, file_name)
            # AutoReader maps these extensions directly, so check can_read() of the reader itself as well
            assert reader(file_path).can_read(), "{} should accept {}".format(reader.__name__, file_name)
            auto = sr.AutoReader(file_path)
            assert auto.reader_cls is reader, "AutoReader chose {} for {}, expected {}".format(
                auto.reader_cls.__name__, file_name, reader.__name__)
            assert [r.__name__ for r in auto.matched_readers] == [reader.__name__], \
                "Only {} should match {}, got {}".format(reader.__name__, file_name, auto.matched_readers)
            assert_same_output(auto.read(), reader(file_path).read(), "AutoReader({})".format(file_name))
