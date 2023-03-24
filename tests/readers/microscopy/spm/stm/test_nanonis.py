import unittest
import sys
import os
import numpy as np
import sidpy
import pytest
from pywget import wget


sys.path.append("../../../../../SciFiReaders/")
import SciFiReaders as sr

root_path = "https://github.com/pycroscopy/SciFiDatasets/blob/main/data/microscopy/spm/stm/"

nanonispy = pytest.importorskip("nanonispy", reason="nanonispy not installed")

class TestNanonisDat(unittest.TestCase):
    # Tests the nanonis_dat reader

    def test_load_test_dat_file(self):
        # Test if the test dat file can be read in correctly
        file_path = 'Bias-Spectroscopy.dat'
        wget.download(root_path + "NanonisReader_BiasSpectroscopy.dat?raw=true", out=file_path)

        data_translator = sr.NanonisDatReader(file_path)
        datasets = data_translator.read(verbose=False)
        os.remove(file_path)
        assert len(datasets)==24, "Length of dataset should be 24 but is instead {}".format(len(datasets))
        metadata = datasets[0].original_metadata
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


class TestNanonisSXM(unittest.TestCase):

    def test_load_nanonis_sxm(self):
        file_path = 'NanonisSXM.sxm'
        wget.download(root_path + "NanonisReader_COOx_sample2286.sxm?raw=true", out=file_path)
        import time
        time.sleep(10)
        reader = sr.NanonisSXMReader(file_path)

        datasets = reader.read()
        os.remove(file_path)
        assert len(datasets)==20, "Length of dataset should be 20 but is instead {}".format(len(datasets))
        for ind in range(20):
            assert type(datasets[ind]) == sidpy.sid.dataset.Dataset, "Type of dataset expected \
            is sidpy.Dataset, received {}".format(type(datasets[ind]))
            assert datasets[ind].shape == (256,256), "Shape of dataset should be (256,256) but instead is {}".format(datasets[ind].shape)
        
        metadata = datasets[0].original_metadata
        original_metadata = {'Channel': '14',
        'Name': 'Z',
        'Unit': 'm',
        'Direction': 'forward',
        'Calibration': '-1.260E-7',
        'Offset': '0.000E+0',
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
        'scan_angle': '9.000E+1',
        'scan_dir': 'up',
        'bias': 0.0,
        'z-controller': {'Name': ('cAFM',),
        'on': ('1',),
        'Setpoint': ('2.000E+0 V',),
        'P-gain': ('5.167E-9 m/V',),
        'I-gain': ('3.059E-5 m/V/s',),
        'T-const': ('1.689E-4 s',)},
        'comment': 'New sample from Kevin CoOx nanosheets',
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
        data_descriptors = ['Z (m)',
        'Z (m)',
        'Vert._Deflection (V)',
        'Vert._Deflection (V)',
        'Horiz._Deflection (V)',
        'Horiz._Deflection (V)',
        'Amplitude2 (V)',
        'Amplitude2 (V)',
        'Phase_2 (V)',
        'Phase_2 (V)',
        'Bias (V)',
        'Bias (V)',
        'Current (A)',
        'Current (A)',
        'Phase (deg)',
        'Phase (deg)',
        'Amplitude (m)',
        'Amplitude (m)',
        'Frequency_Shift (Hz)',
        'Frequency_Shift (Hz)']

        for ind in range(20):
            data_descriptor = datasets[ind].data_descriptor
            assert data_descriptor == data_descriptors[ind], "Expected data descriptor {} \
            but received {}".format(data_descriptors[ind], data_descriptor)

        for key in original_metadata:
            if type(original_metadata[key]) == np.ndarray:
                assert original_metadata[key].all() == metadata[key].all(), "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])
            else:
                assert original_metadata[key] == metadata[key], "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])


class TestNanonis3ds(unittest.TestCase):

    def test_load_nanonis_3ds(self):
        file_path = 'Nanonis3ds.3ds'
        wget.download(root_path + "NanonisReader_STS_grid_lockin.3ds?raw=true", out=file_path)

        reader = sr.Nanonis3dsReader(file_path)
        datasets = reader.read()
        os.remove(file_path)
        assert len(datasets)==4, "Length of dataset should be 4 but is instead {}".format(len(datasets))
        for ind in range(4):
            assert type(datasets[ind]) == sidpy.sid.dataset.Dataset, "Type of dataset expected \
            is sidpy.Dataset, received {}".format(type(datasets[ind]))
            assert datasets[ind].shape == (30,30,200), "Shape of dataset should be (30,30,200) but instead is {}".format(datasets[ind].shape)
        
        metadata = datasets[0].original_metadata
        original_metadata = {'Name': 'Current',
        'Direction': 'forward',
        'Unit': 'A',
        'dim_px': [30, 30],
        'pos_xy': [8.451877e-08, 6.329924e-07],
        'size_xy': [5e-09, 5e-09],
        'angle': 45.0,
        'sweep_signal': 'Bias (V)',
        'num_parameters': 10,
        'experiment_size': 3200,
        'num_sweep_signal': 200,
        'num_channels': 4,
        'measure_delay': 0.0,
        'experiment_name': 'Experiment',
        'start_time': 0.0,
        'end_time': 1000.0,
        'user': '',
        'comment': 'Default values for delay before measuring (s), Start time and End time fields were used! Beware!',
        'Date': '04.06.2016 20:13:23',
        'Sweep Start': -0.2199999988079071,
        'Sweep End': 0.2199999988079071}

        data_descriptors = ['Current (A)', 'LockinX (V)', 'LockinY (V)','Bias_m (V)']
        for ind in range(len(data_descriptors)):
            data_descriptor = datasets[ind].data_descriptor
            assert data_descriptor == data_descriptors[ind], "Expected data descriptor {} \
            but received {}".format(data_descriptors[ind], data_descriptor)

        for key in original_metadata:
            if type(original_metadata[key]) == np.ndarray:
                assert original_metadata[key].all() == metadata[key].all(), "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])
            else:
                assert original_metadata[key] == metadata[key], "Metadata incorrect for key {}, should be {} " \
                    "but was read as {}".format(key, original_metadata[key], metadata[key])




        
