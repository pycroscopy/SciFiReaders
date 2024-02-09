"""
Created on Fri Jan 25 2024

@author: Boris Slautin
"""

import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader

try:
    import anasyspythontools as apt
except ModuleNotFoundError:
    print("You don't have anasyspythontools installed. \
    If you wish to open axz files, you will need to install it \
    (pip install anasyspythontools) before attempting.")
    apt = None


class AxzReader(Reader):
    """
    Extracts data and metadata from Analysis Studio AFM-IR files (.axz) files containing
    images or spectra
    """
    def __init__(self, file_path, *args, **kwargs):
        if apt == None:
            raise ModuleNotFoundError('You attempted to load an .axz file, but this requires anasyspythontools.\n \
            Please Load it with pip install anasyspythontools , restart and retry')

        super().__init__(file_path, *args, **kwargs)

        self.datasets = {}

    def read(self, verbose=False):
        '''
        Reads the file given in file_path into a sidpy dataset

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging

        Returns
        -------
        sidpy.Dataset : Dict with sidpy.Dataset objects.
                    Multi-channel inputs are separated into individual dataset objects
        '''

        file_path = self._input_file_path

        _file = apt.read(file_path)

        _images  = _file.HeightMaps
        _spectra = _file.RenderedSpectra

        channel_number = 0
        if (_images is not None) and (len(_images) > 0):
            for key in _images.keys():
                dataset = self._read_image(_images[key])
                key_channel = f"Channel_{int(channel_number):03d}"
                self.datasets[key_channel] = dataset
                channel_number += 1

        if (_spectra is not None) and (len(_spectra) > 0):
            for key in _spectra.keys():
                dataset = self._read_spectrum(_spectra[key])
                key_channel = f"Channel_{int(channel_number):03d}"
                self.datasets[key_channel] = dataset
                channel_number += 1

        return self.datasets

    def _read_image(self, obj):
        # Convert it to sidpy dataset object
        data = obj['SampleBase64'].T
        title = obj['Label']
        units = str(obj['UnitPrefix']) + str(obj['Units'])

        sizeX, sizeY = float(obj['Size']['X']), float(obj['Size']['Y'])
        resX, resY = int(obj['Resolution']['X']), int(obj['Resolution']['Y'])

        data_set = sid.Dataset.from_array(data)
        data_set.data_type = 'image'
        data_set.title = title
        data_set.units = units

        data_set.set_dimension(0, sid.Dimension(np.linspace(0, sizeX , resX), 'x'))
        data_set.x.dimension_type = 'spatial'
        data_set.x.quantity = 'distance'
        data_set.x.units = 'um'

        data_set.set_dimension(1, sid.Dimension(np.linspace(0, sizeY , resY), 'y'))
        data_set.y.dimension_type = 'spatial'
        data_set.y.quantity = 'distance'
        data_set.y.units = 'um'

        data_set.metadata = self._image_metadata(obj)

        return data_set

    def _image_metadata(self, obj):
        metadata = {}
        metadata['TimeStamp'] = obj['TimeStamp']
        for key in obj['Tags']:
            metadata[key] = obj['Tags'][key]

        loc = {}
        for key in obj['Position'].attrs:
            loc[key] = obj['Position'][key]
        metadata['Location'] = loc

        resol = {}
        for key in obj['Resolution'].attrs:
            resol[key] = obj['Resolution'][key]
        metadata['Resolution'] = resol

        rot = {}
        for key in obj['Rotation'].attrs:
            rot[key] = obj['Rotation'][key]
        metadata['Rotation'] = rot

        return metadata

    def _read_spectrum(self, obj):
        data   = obj['Background']['signal']
        data_x = obj['Background']['wn']
        title = obj['Label']

        posX, posY = float(obj['Location']['X']), float(obj['Location']['Y'])

        data_set = sid.Dataset.from_array(data)
        data_set.title = title
        data_set.data_type = 'spectrum'
        data_set.quantity = 'intensity'
        data_set.units = obj['Background']['Units']

        data_set.set_dimension(0, sid.Dimension(data_x, 'wavenumber'))
        data_set.dim_0.dimension_type = 'spectral'
        data_set.dim_0.quantity = 'wavenumber'
        data_set.dim_0.units = 'cm-1'#?

        data_set.metadata = self._spectrum_metadata(obj)
        return data_set

    def _spectrum_metadata(self, obj):
        metadata = {}
        metadata['TimeStamp'] = obj['TimeStamp']
        for key in obj['Background'].attrs:
            if key not in ['signal', 'Table', 'wn'] and '.' not in key:
                metadata[key] = obj['Background'][key]

        loc = {}
        for key in obj['Location']:
            loc[key] = obj['Location'][key]
        metadata['Location'] = loc

        win_data = {}
        for key in obj['FreqWindowData'].attrs:
            win_data[key] = obj['FreqWindowData'][key]

        metadata['FreqWindowData'] = win_data

        return metadata