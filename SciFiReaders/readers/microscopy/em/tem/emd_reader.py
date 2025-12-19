
""" 
################################################################################
# Python class for reading FEI Velox .emd files into sidpy Dataset
# and extracting all metadata
#
# Written by Gerd Duscher, UTK 2021
# update 08/2025 - improved EDS data reading
#
################################################################################
"""
import json
import h5py
import numpy as np
# import dask.array as da
from numba import njit
import sidpy

__version__ = '0.1beta'
__all__ = ["EMDReader", "__version__"]

DEBUG_LEVEL = 0  # 0=none, 1-3=basic, 4-5=simple, 6-10 verbose


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
    def __init__(self, file_path:str, sum_frames:bool=False, no_eds:bool=False):
        """
        Initialize an EMDReader instance.

        Parameters:
            file_path (str): Path to the HDF5 (.emd) file to be read.
            sum_frames (bool, optional): If True, sum all frames in the dataset. Defaults to False.
            no_eds (bool, optional): If True, disables EDS (Energy Dispersive Spectroscopy) 
            data handling. Defaults to False.

        Attributes:
            _h5_file (h5py.File): The opened HDF5 file object.
            datasets (dict): Dictionary to store dataset references.
            channel_number (int): The current channel number (default is 0).
            key (str): Formatted string key for the current channel.
            data_array (ndarray or None): Array to hold data from the file.
            metadata (dict or None): Metadata extracted from the file.
            label_dict (dict): Dictionary for label mapping.
            no_eds (bool): Indicates if EDS data handling is disabled.
            sum_frames (bool): Indicates if frames should be summed.
            number_of_frames (int): Number of frames in the dataset (default is 1).
        """
        super().__init__(file_path)

        # Let h5py raise an OS error if a non-HDF5 file was provided
        self._h5_file: h5py.File = h5py.File(file_path, mode='r+')

        self.datasets = {}
        self.channel_number = 0
        self.key = f"Channel_{int(self.channel_number):03d}"
        self.data_array = None
        self.metadata = None
        self.label_dict = {}
        self.no_eds = no_eds
        self.sum_frames = sum_frames
        self.number_of_frames = 1
        self.image_key = ''
        self.bin_xy = 1

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
        return False

    def read(self, eds_stream:bool=False, bin_xy:int=2):
        """
        Reads all available datasets in FEI Velox style hdf5 files with .edm

        Parameters
        ----------
        eds_stream: boolean
            switch to return spectrum image (default - False) or original spectrum stream (True)
        bin_xy: int
            binning factor for EDS spectrum size reduction

        Returns
        -------
        datasets: list of sidpy.Dataset objects
            Datasets present in the provided file
        """

        if 'Data' not in self._h5_file:
            raise TypeError('Velox EMD File is empty')

        number_of_datasets = 0

        self.bin_xy = bin_xy
        self.image_key = ''

        for key in self._h5_file['Data'].keys():  # type: str
            if key == 'SpectrumStream':
                number_of_datasets += len(self._h5_file['Data']['SpectrumStream'].keys())
        for key in self._h5_file['Data'].keys():
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
        self.close()
        return self.datasets

    def get_data(self, image_key):
        """Get the image data and metadata from the file."""
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
        else:
            image_display_group = self._h5_file.get('Displays/ImageDisplay')
            if image_display_group is not None:
                for key in image_display_group.keys():
                    v = json.loads(
                        image_display_group[key][0].decode('utf-8'))
                    if 'data' in v:
                        data = json.loads(self._h5_file[v['data']][()][0].decode('utf-8'))
                        data_key = data['dataPath'].split('/')[-1]  # key in data group
                        self.label_dict[data_key] = v['title']


    def get_eds(self, eds_stream=False):
        """Get the EDS data from the file."""
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
                chunks= [data_array.shape[1], 32, data_array.shape[2]]
                if data_array.shape[0]> chunks[0]:
                    chunks[0] = data_array.shape[0]
                if data_array.shape[1]> chunks[1]:
                    chunks[1] = data_array.shape[1]
            self.datasets[key] = sidpy.Dataset.from_array(data_array, chunks=chunks)

        self.data_array=np.zeros([1,1])
        self.datasets[key].original_metadata = self.metadata
        detectors = self.datasets[key].original_metadata.get('Detectors', {})

        print(detectors)
        if eds_stream:
            pass
        else:
            offset = 0
            dispersion = 1.
            for detector in detectors.values():
                if self.metadata.get('BinaryResult', {}).get('Detector') in detector.get('DetectorName', ''):
                    offset = float(detector.get('OffsetEnergy', 0))
                    dispersion = float(detector.get('Dispersion', 0))*self.bin_xy*1.003
            self.datasets[key].units = 'counts'
            self.datasets[key].quantity = 'intensity'
            self.datasets[key].modality = 'EDS'

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

                scale =  self.metadata.get('BinaryResult', {}).get('PixelSize', {})
                scale_x = float(scale.get('width', 1e-9)) * 1e9
                scale_y = float(scale.get('height', 1e-9)) * 1e9

                self.datasets[key].set_dimension(0, sidpy.Dimension(
                                            np.arange(self.datasets[key].shape[0]) * scale_x,
                                            name='x', units='nm',
                                            quantity='distance',
                                            dimension_type='spatial'))
                self.datasets[key].set_dimension(1, sidpy.Dimension(np.arange(
                                            self.datasets[key].shape[1]) * scale_y,
                                            name='y', units='nm',
                                            quantity='distance',
                                            dimension_type='spatial'))
                self.datasets[key].set_dimension(2, sidpy.Dimension(
                                            energy_scale,
                                            name='energy_scale', units='eV',
                                            quantity='energy',
                                            dimension_type='spectral'))

    def get_eds_spectrum(self) -> np.ndarray:
        """Get the EDS spectrum."""
        acquisition = self.metadata.get('AcquisitionSettings', {})

        scan_area = self.metadata.get('Scan', {}).get('ScanArea', {})
        scan_size = self.metadata.get('Scan', {}).get('ScanSize', {})

        if len(scan_area) * len(scan_size) > 0:
            size_x = float(scan_size.get('width', 1)) * float(scan_area.get('right', 1))
            size_x -= float(scan_size.get('width', 1)) * float(scan_area.get('left', 0))
            size_y = float(scan_size.get('height', 1)) * float(scan_area.get('bottom', 1))
            size_y -= float(scan_size.get('height', 1)) * float(scan_area.get('top', 0))
            size_x = int(size_x)
            size_y = int(size_y)
        else:
            raster_scan = acquisition.get('RasterScanDefinition', {})
            size_x = int(raster_scan.get('Width', 1))
            size_y = int(raster_scan.get('Height', 1))

        spectrum_size = int(acquisition.get('bincount', 0))
        self.number_of_frames = np.ceil((self.data_array[:, 0] == 65535).sum())
        self.number_of_frames = int(self.number_of_frames / (size_x * size_y))

        data_array = np.zeros((int(size_x*size_y), int(spectrum_size/self.bin_xy)),dtype=np.ushort)

        data, frame = get_stream(data_array, size_x*size_y, self.data_array[:, 0], self.bin_xy)

        self.number_of_frames = frame
        return np.reshape(data, (size_x, size_y, int(spectrum_size/self.bin_xy)))

    def get_image(self):
        """ Get the image data."""
        key = f"Channel_{int(self.channel_number):03d}"
        self.key = key
        self.channel_number += 1

        if self.metadata['BinaryResult']['PixelUnitX'] == '1/m':
            names = ['u', 'v']
            units = '1/nm'
            quantity = 'reciprocal distance'
            dimension_type='reciprocal'
            to_nm = 1e-9
        else:
            names = ['x', 'y']
            units = 'nm'
            quantity = 'distance'
            dimension_type='spatial'
            to_nm = 1e9
        scale = self.metadata.get('BinaryResult', {})
        scale_x = float(scale.get('PixelSize', {}).get('width', 0)) * to_nm
        scale_y = float(scale.get('PixelSize', {}).get('height', 0)) * to_nm
        offset_x = float(scale.get('Offset', {}).get('x', 0)) * to_nm
        offset_y = float(scale.get('Offset', {}).get('y', 0)) * to_nm

        if self.sum_frames:
            data_array = np.zeros([self.data_array.shape[0], self.data_array.shape[1], 1])
            for i in range(self.data_array.shape[2]):
                data_array[:, :, 0] += self.data_array[:, :, i]
            self.data_array = data_array

        if self.data_array.shape[2] == 1:
            self.datasets[key] = sidpy.Dataset.from_array(self.data_array[:, :, 0])
            self.datasets[key].data_type = 'image'
            self.datasets[key].set_dimension(0, sidpy.Dimension(
                                    np.arange(self.data_array.shape[0]) * scale_x + offset_x,
                                    name=names[0], units=units,
                                    quantity=quantity,
                                    dimension_type=dimension_type))
            self.datasets[key].set_dimension(1, sidpy.Dimension(
                                    np.arange(self.data_array.shape[1]) * scale_y + offset_y,
                                    name=names[1], units=units,
                                    quantity=quantity,
                                    dimension_type=dimension_type))
        else:
            # There is a problem with random access of data due to chunking in hdf5 files
            # Speed-up copied from hyperspy.ioplugins.EMDReader.FEIEMDReader
            data_array = np.empty(self.data_array.shape)
            self.data_array.read_direct(data_array)
            self.data_array = np.rollaxis(data_array, axis=2)

            self.datasets[key] = sidpy.Dataset.from_array(self.data_array)
            self.datasets[key].data_type = 'image_stack'

            self.datasets[key].set_dimension(0, sidpy.Dimension(
                                    np.arange(self.data_array.shape[0]),
                                    name='frame', units='frame',
                                    quantity='time',
                                    dimension_type='temporal'))
            self.datasets[key].set_dimension(1, sidpy.Dimension(
                                    np.arange(self.data_array.shape[1]) * scale_x + offset_x,
                                    name=names[0], units=units,
                                    quantity=quantity,
                                    dimension_type=dimension_type))
            self.datasets[key].set_dimension(2, sidpy.Dimension(
                                    np.arange(self.data_array.shape[2]) * scale_y + offset_y,
                                    name=names[1], units=units,
                                    quantity=quantity,
                                    dimension_type=dimension_type))
        self.datasets[key].original_metadata = self.metadata

        self.datasets[key].units = 'counts'
        self.datasets[key].quantity = 'intensity'
        self.datasets[key].modality = 'image'

        if self.image_key in self.label_dict:
            self.datasets[key].title = self.label_dict[self.image_key]
        self.data_array=np.zeros([1,1])

    def extract_crucial_metadata(self, key):
        """ Extract some crucial metadata from the original metadata."""
        metadata = self.datasets[key].original_metadata
        experiment = {'detector': metadata.get('BinaryResult', {}).get('Detector', ''),
                      'acceleration_voltage': float(metadata.get('Optics', {}).get('AccelerationVoltage', 0)),
                      'microscope': metadata.get('Instrument', {}).get('InstrumentClass', ''),
                      'start_date_time': int(metadata.get('Acquisition', {}).get('AcquisitionStartDatetime', {}).get('DateTime', 0)),
                      'collection_angle': 0.0,
                      'convergence_angle': 0.0}
        if metadata.get('Optics', {}).get('ProbeMode') == "1":
            experiment['probe_mode'] = "convergent"
            experiment['convergence_angle'] = float(metadata.get('Optics', {}).get('BeamConvergence', 0))
        else:  # metadata['Optics']['ProbeMode'] == "2":
            experiment['probe_mode'] = "parallel"
        stage_dict = metadata.get('Stage', {})
        experiment['stage'] = {"holder": "",
                               "position": {"x": float(stage_dict.get('Position', {}).get('x', 0)),
                                            "y": float(stage_dict.get('Position', {}).get('y', 0)),
                                            "z": float(stage_dict.get('Position', {}).get('z', 0))},
                                "tilt": {"alpha": float(stage_dict.get('AlphaTilt', 0)),
                                         "beta": float(stage_dict.get('BetaTilt', 0))}}
        model = self.datasets[key].original_metadata.get('Instrument', {}).get('InstrumentModel', '')
        instrument_id = self.datasets[key].original_metadata.get('Instrument', {}).get('InstrumentId', '')
        experiment['instrument'] = model + str(instrument_id)
        experiment['current'] = float(metadata.get('Optics', {}).get('LastMeasuredScreenCurrent', 0.0))
        experiment['pixel_time'] = float(metadata.get('Scan', {}).get('DwellTime', 0.0))
        experiment['exposure_time'] = float(metadata.get('Scan', {}).get('FrameTime', 0.0))

        if isinstance(metadata.get('Sample'), dict):
            experiment['sample'] = metadata['Sample'].get('SampleDescription', '')
            experiment['sample_id'] = metadata['Sample'].get('SampleId', '')
        eds = {}
        used_detector = experiment.get('detector', 'unknown')
        for detector in metadata.get('Detectors', {}).values():
            if used_detector in detector.get('DetectorName', ''):
                begin = detector.get('CollectionAngleRange', {}).get('begin', -1)
                experiment['collection_angle'] = float(begin)
                end = detector.get('CollectionAngleRange', {}).get('end', -1)
                experiment['collection_angle_end'] = float(end)
                if 'SuperX' in detector['DetectorName']:
                    start_energy = int(detector.get('BeginEnergy', 120))
                    energy_scale = self.datasets[key].get_spectral_dims(return_axis=True)
                    if len(energy_scale) >0:
                        start_channel = 100
                    else:
                        start_channel = np.searchsorted(energy_scale, start_energy)
                    eds = {'detector': {'layers': {13: {'thickness': 0.05*1e-6, 'Z': 13, 'element': 'Al'}},
                                        'SiDeadThickness': .13 *1e-6,  # in m
                                        'SiLiveThickness': 0.05 , # in m
                                        'detector_area': 30 * 1e-6, #in m2
                                        'energy_resolution': 125,  # in eV
                                        'start_energy': start_energy,  # in eV
                                        'start_channel': int(start_channel),
                                        'ElevationAngle': float(detector.get('ElevationAngle', 0.0)), 
                                        'AzimuthAngle': float(detector.get('AzimuthAngle', 0.0)),
                                        'RealTime': float(detector.get('RealTime', 0.0)), 
                                        'LiveTime': float(detector.get('LiveTime', 0.0))}}
        self.datasets[key].metadata['experiment'] = experiment.copy()
        if eds:
            self.datasets[key].metadata['EDS'] = eds.copy()

        if self.datasets[key].title == 'generic':
            self.datasets[key].title = experiment['detector']

    def close(self):
        """ Close the h5 file."""
        self._h5_file.close()

@njit(cache=True)
def get_stream(data, size, data_stream, bin_xy):
    """ Get the EDS spectrum from the stream."""
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
        else:
            data[pixel_number, int(value/bin_xy-0.2)] += 1
    return data, frame
