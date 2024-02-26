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
import dask.array as da
from numba import njit
import sidpy
try:
    from tqdm.auto import tqdm
    tqdm_available = True
except ImportError:
    tqdm_available = False

__all__ = ["EMDReader", "version"]

version = '0.1beta'


debugLevel = 0  # 0=none, 1-3=basic, 4-5=simple, 6-10 verbose

if sys.version_info.major == 3:
    unicode = str


class EMDReader(sidpy.Reader):
    
    """
    Creates an instance of EMDReader which can read one or more HDF5
    datasets formatted in the FEI Velox style EDM file

    We can read Images, and SpectrumStreams (SpectrumImages and Spectra).
    Please note that all original metadata are retained in each sidpy dataset.

    Parameters
    ----------
    file_path : str
        Path to a HDF5 file
    Return
    ------
    datasets: dict
        dictionary of sidpy.Datasets
    """
    def __init__(self, file_path, sum_frames=False, no_eds=False):
        super(EMDReader, self).__init__(file_path)

        # Let h5py raise an OS error if a non-HDF5 file was provided
        self._h5_file = h5py.File(file_path, mode='r+')

        self.datasets = {}
        self.channel_number = 0
        self.key = f"Channel_{int(self.channel_number):03d}"
        self.data_array = None
        self.metadata = None
        self.label_dict = {}
        self.no_eds = no_eds
        self.sum_frames = sum_frames
            
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
    
        number_of_datasets = 0
        use_tqdm = False
        for key in self._h5_file['Data']:
            if key == 'SpectrumStream':
                number_of_datasets += len(self._h5_file['Data']['SpectrumStream'].keys())
        if number_of_datasets > 1:
            progress_bar = tqdm(total=number_of_datasets)  # Initialise
            use_tqdm = tqdm_available
        for key in self._h5_file['Data']:
            self.image_key = 'None'
            self._parse_image_display()
            if key == 'Image':
                for self.image_key in self._h5_file['Data']['Image']:
                    self.get_data('Data/Image/' + self.image_key)
                    self.get_image()
                    self.extract_crucial_metadata(self.key)
            elif key == 'SpectrumStream':
                if not self.no_eds:
                    for stream_key in self._h5_file['Data']['SpectrumStream']:
                        self.get_data('Data/SpectrumStream/' + stream_key)
                        self.get_eds(eds_stream)
                        self.extract_crucial_metadata(self.key)
                        if use_tqdm:
                            progress_bar.update(1)
        if use_tqdm:
            progress_bar.close()
        self.close()
        return self.datasets

    def get_data(self, image_key):
        self.data_array = self._h5_file[image_key]['Data']
        metadata_array = self._h5_file[image_key]['Metadata'][:, 0]
        metadata_string = metadata_array.tobytes().decode("utf-8")
        self.metadata = dict(json.loads(metadata_string.rstrip('\x00')))
        if 'AcquisitionSettings' in self._h5_file[image_key]:
            self.metadata['AcquisitionSettings'] = json.loads(self._h5_file[image_key]['AcquisitionSettings'][0])        

    def _parse_image_display(self):
        ### Read image label according to hyperspy EMDReader
        image_display_group = self._h5_file.get('Presentation/Displays/ImageDisplay')
        if image_display_group is not None:
            for key in image_display_group.keys():
                v = json.loads(
                    image_display_group[key][0].decode('utf-8'))
                data_key = v['dataPath'].split('/')[-1]  # key in data group
                self.label_dict[data_key] = v['display']['label']

    def get_eds(self, eds_stream=False):
        if 'AcquisitionSettings' not in self.metadata:
            eds_stream = True
        key = f"Channel_{int(self.channel_number):03d}"
        self.key = key
        self.channel_number += 1
        if eds_stream:
            self.datasets[key] = sidpy.Dataset.from_array(self.data_array)
        else:
            data_array = self.get_eds_spectrum()
            if data_array.shape[0] == 1 and data_array.shape[1] == 1:
                data_array = np.squeeze(data_array)
                chunks = 1
            else:
                chunks= [32, 32, data_array.shape[2]]
                if data_array.shape[0]> chunks[0]:
                    chunks[0] = data_array.shape[0]
                if data_array.shape[1]> chunks[1]:
                    chunks[1] = data_array.shape[1]
                
            self.datasets[key] = sidpy.Dataset.from_array(data_array, chunks=chunks)
       
        self.data_array=np.zeros([1,1])
        self.datasets[key].original_metadata = self.metadata
        detectors = self.datasets[key].original_metadata['Detectors']
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

            self.datasets[key].units = 'counts'
            self.datasets[key].quantity = 'intensity'
            energy_scale = np.arange(self.datasets[key].shape[-1]) * dispersion + offset

            if self.datasets[key].ndim == 1:
                self.datasets[key].data_type = 'spectrum'

                self.datasets[key].set_dimension(0, sidpy.Dimension(energy_scale,
                                                                   name='energy_scale', units='eV',
                                                                   quantity='energy',
                                                                   dimension_type='spectral'))

            else:
                self.datasets[key].data_type = 'spectral_image'
                print(self.datasets[key].shape)
                
                scale_x = float(self.metadata['BinaryResult']['PixelSize']['width']) * 1e9
                scale_y = float(self.metadata['BinaryResult']['PixelSize']['height']) * 1e9

                self.datasets[key].set_dimension(0, sidpy.Dimension(np.arange(self.datasets[key].shape[0]) * scale_x,
                                                                   name='x', units='nm',
                                                                   quantity='distance',
                                                                   dimension_type='spatial'))
                self.datasets[key].set_dimension(1, sidpy.Dimension(np.arange(self.datasets[key].shape[1]) * scale_y,
                                                                   name='y', units='nm',
                                                                   quantity='distance',
                                                                   dimension_type='spatial'))
                self.datasets[key].set_dimension(2, sidpy.Dimension(energy_scale,
                                                                   name='energy_scale', units='eV',
                                                                   quantity='energy',
                                                                   dimension_type='spectral'))
                
    
    def get_eds_spectrum(self):
        acquisition = self.metadata['AcquisitionSettings']
        
        size_x = 1
        size_y = 1
        if 'Scan' in self.metadata:
            scan = self.metadata['Scan']
            if 'ScanArea' in scan:
                size_x = int(float(scan['ScanSize']['width']) * float(scan['ScanArea']['right'])-float(scan['ScanSize']['width']) * float(scan['ScanArea']['left']))
                size_y = int(float(scan['ScanSize']['height']) * float(scan['ScanArea']['bottom'])-float(scan['ScanSize']['height']) * float(scan['ScanArea']['top']))
            
        if 'RasterScanDefinition' in acquisition:
            size_x = int(acquisition['RasterScanDefinition']['Width'])
            size_y = int(acquisition['RasterScanDefinition']['Height'])
        spectrum_size = int(acquisition['bincount'])

        self.number_of_frames = int(np.ceil((self.data_array[:, 0] == 65535).sum() / (size_x * size_y)))
        # print(size_x,size_y,number_of_frames)
        data_array = np.zeros((size_x * size_y, spectrum_size),dtype=np.ushort)
        # progress = tqdm(total=number_of_frames)
        
        data, frame = get_stream(data_array, size_x*size_y, self.data_array[:, 0])
        
        self.number_of_frames = frame
        return np.reshape(data, (size_x, size_y, spectrum_size))

    def get_image(self):
        key = f"Channel_{int(self.channel_number):03d}"
        self.key = key
        self.channel_number += 1
        
        if self.metadata['BinaryResult']['PixelUnitX'] == '1/m':
            units = '1/nm'
            quantity = 'reciprocal distance'
            dimension_type='reciprocal'
            to_nm = 1e-9
        else:
            units = 'nm'
            quantity = 'distance'
            dimension_type='spatial'
            to_nm = 1e9

        scale_x = float(self.metadata['BinaryResult']['PixelSize']['width']) * to_nm
        scale_y = float(self.metadata['BinaryResult']['PixelSize']['height']) * to_nm
        offset_x = float(self.metadata['BinaryResult']['Offset']['x']) * to_nm
        offset_y = float(self.metadata['BinaryResult']['Offset']['y'])  * to_nm
        
        if self.sum_frames:
            data_array = np.zeros([self.data_array.shape[0], self.data_array.shape[1], 1])
            for i in range(self.data_array.shape[2]):
                data_array[:, :, 0] += self.data_array[:, :, i]
            self.data_array = data_array

        if self.data_array.shape[2] == 1:
            self.datasets[key] = sidpy.Dataset.from_array(self.data_array[:, :, 0])
            self.datasets[key].data_type = 'image'
            self.datasets[key].set_dimension(0, sidpy.Dimension(np.arange(self.data_array.shape[0]) * scale_x + offset_x,
                                                               name='x', units=units,
                                                               quantity=quantity,
                                                               dimension_type=dimension_type))
            self.datasets[key].set_dimension(1, sidpy.Dimension(np.arange(self.data_array.shape[1]) * scale_y + offset_y,
                                                               name='y', units=units,
                                                               quantity=quantity,
                                                               dimension_type='spatial'))
        else:
            # There is a problem with random access of data due to chunking in hdf5 files
            # Speed-up copied from hyperspy.ioplugins.EMDReader.FEIEMDReader
            data_array = np.empty(self.data_array.shape)
            self.data_array.read_direct(data_array)
            self.data_array = np.rollaxis(data_array, axis=2)
            
            self.datasets[key] = sidpy.Dataset.from_array(self.data_array)
            self.datasets[key].data_type = 'image_stack'

            self.datasets[key].set_dimension(0, sidpy.Dimension(np.arange(self.data_array.shape[0]),
                                                               name='frame', units='frame',
                                                               quantity='time',
                                                               dimension_type='temporal'))
            self.datasets[key].set_dimension(1, sidpy.Dimension(np.arange(self.data_array.shape[1]) * scale_x + offset_x,
                                                               name='x', units=units,
                                                               quantity=quantity,
                                                               dimension_type=dimension_type))
            self.datasets[key].set_dimension(2, sidpy.Dimension(np.arange(self.data_array.shape[2]) * scale_y + offset_y,
                                                               name='y', units=units,
                                                               quantity=quantity,
                                                               dimension_type='spatial'))
        self.datasets[key].original_metadata = self.metadata

        if not True:
            print('nothing')

        self.datasets[key].units = 'counts'
        self.datasets[key].quantity = 'intensity'
        if self.image_key in self.label_dict:
            self.datasets[key].title = self.label_dict[self.image_key]
        self.data_array=np.zeros([1,1])

    def extract_crucial_metadata(self, key):
        metadata = self.datasets[key].original_metadata
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

        self.datasets[key].metadata['experiment'] = experiment
        if self.datasets[key].title == 'generic':
            self.datasets[key].title = experiment['detector']

    def close(self):
        self._h5_file.close()

@njit(cache=True)
def get_stream(data, size, data_stream):
    #for value in self.data_array[:, 0]:
    #from tqdm.auto import trange, tqdm
    pixel_number = 0
    frame = 0
    for value in data_stream:
        if value == 65535:
            pixel_number += 1
            if pixel_number >= size:
                pixel_number = 0
                frame += 1
                # print(frame)
                # progress.update(1)
        else:
            data[pixel_number, value] += 1
    return data, frame