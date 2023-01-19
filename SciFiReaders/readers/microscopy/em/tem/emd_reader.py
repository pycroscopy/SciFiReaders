#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

################################################################################
# Python class for reading FEI Velox .emd files into sidpy Dataset
# and extracting all metadata
#
# Written by Gerd Duscher, UTK 2021
#
# Works for python 3
#
################################################################################
import json
import h5py
import sys
import numpy as np

import sidpy

__all__ = ["EMDReader", "version"]

version = '0.1beta'


debugLevel = 0  # 0=none, 1-3=basic, 4-5=simple, 6-10 verbose

if sys.version_info.major == 3:
    unicode = str


class EMDReader(sidpy.Reader):
    def __init__(self, file_path):
        """
        Creates an instance of EMDReader which can read one or more HDF5
        datasets formatted in the FEI Velox style EDM file

        We can read Images, and SpectrumStreams (SpectrumImages and Spectra).
        Please note that all original metadata are retained in each sidpy dataset.

        Parameters
        ----------
        file_path : str
            Path to a HDF5 file
        """

        super(EMDReader, self).__init__(file_path)

        # Let h5py raise an OS error if a non-HDF5 file was provided
        self._h5_file = h5py.File(file_path, mode='r+')

        self.datasets = []
        self.data_array = None
        self.metadata = None
        self.number_of_frames = 1

    def can_read(self):
        """
        Checks whether or not this Reader can read the provided file

        Returns
        -------
        bool :
            True if this Reader can read the provided file
            Else, False
        """
        if 'Application' in self._h5_file:
            return 'Velox' in self._h5_file['Application']
        else:
            return False

    def read(self, eds_stream=False):
        """
        Reads all available datasets in FEI Velox style hdf5 files with .edm

        Parameters
        ----------
        eds_stream: boolean
            switch to return spectrum image (default - False) or original spectrum stream (True)

        Returns
        -------
        datasets: list of sidpy.Dataset objects
            Datasets present in the provided file
        """

        if 'Data' not in self._h5_file:
            raise TypeError('Velox EMD File is empty')
        for key in self._h5_file['Data']:
            if key == 'Image':
                for image_key in self._h5_file['Data']['Image']:
                    self.get_data('Data/Image/' + image_key)
                    self.get_image()
                    self.get_metadata(-1)
            elif key == 'SpectrumStream':
                for stream_key in self._h5_file['Data']['SpectrumStream']:
                    self.get_data('Data/SpectrumStream/' + stream_key)
                    self.get_eds(eds_stream)
                    self.get_metadata(-1)

        self.close()
        return self.datasets

    def get_data(self, image_key):
        self.data_array = self._h5_file[image_key]['Data']
        metadata_array = self._h5_file[image_key]['Metadata'][:, 0]
        metadata_string = metadata_array.tobytes().decode("utf-8")
        self.metadata = dict(json.loads(metadata_string.rstrip('\x00')))
        if 'AcquisitionSettings' in self._h5_file[image_key]:
            self.metadata['AcquisitionSettings'] = json.loads(self._h5_file[image_key]['AcquisitionSettings'][0])

    def get_eds(self, eds_stream=False):
        if 'AcquisitionSettings' not in self.metadata:
            eds_stream = True
        if eds_stream:
            self.datasets.append(sidpy.Dataset.from_array(self.data_array))
        else:
            data_array = self.get_eds_spectrum()
            if data_array.shape[0] == 1 and data_array.shape[1] == 1:
                data_array = np.array(data_array).flatten()
            self.datasets.append(sidpy.Dataset.from_array(data_array))
        # print(self.datasets[-1])

        self.datasets[-1].original_metadata = self.metadata

        detectors = self.datasets[-1].original_metadata['Detectors']
        if eds_stream:
            pass
        else:
            offset = 0.
            dispersion = 1.
            for detector in detectors.values():
                if self.metadata['BinaryResult']['Detector'] in detector['DetectorName']:
                    if 'OffsetEnergy' in detector:
                        offset = float(detector['OffsetEnergy'])
                    if 'Dispersion' in detector:
                        dispersion = float(detector['Dispersion'])

            self.datasets[-1].units = 'counts'
            self.datasets[-1].quantity = 'intensity'
            energy_scale = np.arange(self.datasets[-1].shape[-1]) * dispersion + offset

            if self.datasets[-1].ndim == 1:
                self.datasets[-1].data_type = 'spectrum'

                self.datasets[-1].set_dimension(0, sidpy.Dimension(energy_scale,
                                                                   name='energy_scale', units='eV',
                                                                   quantity='energy',
                                                                   dimension_type='spectral'))

            else:
                self.datasets[-1].data_type = 'spectral_image'
                self.datasets[-1].set_dimension(2, sidpy.Dimension(energy_scale,
                                                                   name='energy_scale', units='eV',
                                                                   quantity='energy',
                                                                   dimension_type='spectral'))
                scale_x = float(self.metadata['BinaryResult']['PixelSize']['width']) * 1e9
                scale_y = float(self.metadata['BinaryResult']['PixelSize']['height']) * 1e9

                self.datasets[-1].set_dimension(0, sidpy.Dimension(np.arange(self.datasets[-1].shape[0]) * scale_x,
                                                                   name='x', units='nm',
                                                                   quantity='distance',
                                                                   dimension_type='spatial'))
                self.datasets[-1].set_dimension(1, sidpy.Dimension(np.arange(self.datasets[-1].shape[1]) * scale_y,
                                                                   name='y', units='nm',
                                                                   quantity='distance',
                                                                   dimension_type='spatial'))

    def get_eds_spectrum(self):
        acquisition = self.metadata['AcquisitionSettings']
        print(acquisition)
        size_x = 1
        size_y = 1
        if 'RasterScanDefinition' in acquisition:
            size_x = int(acquisition['RasterScanDefinition']['Width'])
            size_y = int(acquisition['RasterScanDefinition']['Height'])
        spectrum_size = int(acquisition['bincount'])

        self.number_of_frames = int(np.ceil((self.data_array[:, 0] == 65535).sum() / (size_x * size_y)))
        # print(size_x,size_y,number_of_frames)
        data = np.zeros((size_x * size_y, spectrum_size),dtype=int)
        # progress = tqdm(total=number_of_frames)
        pixel_number = 0
        frame = 0
        for value in self.data_array[:, 0]:
            if value == 65535:
                pixel_number += 1
                if pixel_number >= size_x * size_y:
                    pixel_number = 0
                    frame += 1
                    # print(frame)
                    # progress.update(1)
            else:
                data[pixel_number, value] += 1
        self.number_of_frames = frame
        return np.reshape(data, (size_x, size_y, spectrum_size))

    def get_image(self):

        scale_x = float(self.metadata['BinaryResult']['PixelSize']['width']) * 1e9
        scale_y = float(self.metadata['BinaryResult']['PixelSize']['height']) * 1e9

        if self.data_array.shape[2] == 1:
            self.datasets.append(sidpy.Dataset.from_array(self.data_array[:, :, 0]))
            self.datasets[-1].data_type = 'image'
            self.datasets[-1].set_dimension(0, sidpy.Dimension(np.arange(self.data_array.shape[0]) * scale_x,
                                                               name='x', units='nm',
                                                               quantity='distance',
                                                               dimension_type='spatial'))
            self.datasets[-1].set_dimension(1, sidpy.Dimension(np.arange(self.data_array.shape[1]) * scale_y,
                                                               name='y', units='nm',
                                                               quantity='distance',
                                                               dimension_type='spatial'))
        else:
            # There is a problem with random access of data due to chunking in hdf5 files
            # Speed-up copied from hyperspy.ioplugins.EMDReader.FEIEMDReader

            data_array = np.empty(self.data_array.shape)
            self.data_array.read_direct(data_array)
            self.data_array = np.rollaxis(data_array, axis=2)
            # np.moveaxis(data_array, source=[0, 1, 2], destination=[2, 0, 1])
            
            self.datasets.append(sidpy.Dataset.from_array(self.data_array))
            self.datasets[-1].data_type = 'image_stack'
            self.datasets[-1].set_dimension(0, sidpy.Dimension(np.arange(self.data_array.shape[0]),
                                                               name='frame', units='frame',
                                                               quantity='time',
                                                               dimension_type='temporal'))
            self.datasets[-1].set_dimension(1, sidpy.Dimension(np.arange(self.data_array.shape[1]) * scale_x,
                                                               name='x', units='nm',
                                                               quantity='distance',
                                                               dimension_type='spatial'))
            self.datasets[-1].set_dimension(2, sidpy.Dimension(np.arange(self.data_array.shape[2]) * scale_y,
                                                               name='y', units='nm',
                                                               quantity='distance',
                                                               dimension_type='spatial'))
        self.datasets[-1].original_metadata = self.metadata

        self.datasets[-1].units = 'counts'
        self.datasets[-1].quantity = 'intensity'

    def get_metadata(self, index):
        metadata = self.datasets[index].original_metadata
        experiment = {'detector': metadata['BinaryResult']['Detector'],
                      'acceleration_voltage': float(metadata['Optics']['AccelerationVoltage']),
                      'microscope': metadata['Instrument']['InstrumentClass'],
                      'start_date_time': int(metadata['Acquisition']['AcquisitionStartDatetime']['DateTime'])}

        if metadata['Optics']['ProbeMode'] == "1":
            experiment['probe_mode'] = "convergent"
            if 'BeamConvergence' in metadata['Optics']:
                experiment['convergence_angle'] = float(metadata['Optics']['BeamConvergence'])
        else:  # metadata['Optics']['ProbeMode'] == "2":
            experiment['probe_mode'] = "parallel"
            experiment['convergence_angle'] = 0.0
        experiment['stage'] = {"holder": "",
                               "position": {"x": float(metadata['Stage']['Position']['x']),
                                            "y": float(metadata['Stage']['Position']['y']),
                                            "z": float(metadata['Stage']['Position']['z'])},
                               "tilt": {"alpha": float(metadata['Stage']['AlphaTilt']),
                                        "beta": float(metadata['Stage']['BetaTilt'])}}

        self.datasets[index].metadata['experiment'] = experiment

    def close(self):
        self._h5_file.close()
