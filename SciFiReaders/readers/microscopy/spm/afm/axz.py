"""
Created on Fri Jan 25 2024

@author: Boris Slautin
"""

import numpy as np  # For array operations
import base64
import struct
import sidpy as sid
from sidpy.sid import Reader

#XML reader
import xml.etree.ElementTree as ET

import gzip


class AxzReader(Reader):
    """
    Extracts data and metadata from Analysis Studio AFM-IR files (.axz) files containing
    images or spectra
    """
    def __init__(self, file_path, *args, **kwargs):
        # if apt == None:
        #     raise ModuleNotFoundError('You attempted to load an .axz file, but this requires anasyspythontools.\n \
        #     Please Load it with pip install anasyspythontools , restart and retry')

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

        _file = self._file_to_dict(file_path)

        _images  = _file['HeightMaps']
        self._images = _images
        _spectra = _file['RenderedSpectra']

        self._file = _file

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

    def _file_to_dict(self, filepath):
        with gzip.open(filepath) as f:
            f_data = ET.iterparse(f)
            for event, el in f_data:
                el.tag = el.tag.split('}', -1)[-1]

        data = f_data.root

        res_dict = {'HeightMaps':{},
                    'RenderedSpectra':{}}

        for items in data:
            if items.tag == 'HeightMaps':
                for i, item in enumerate(items):
                    res_dict['HeightMaps'][i] = self._xml_to_dict(item)
            elif items.tag == 'RenderedSpectra':
                for i, item in enumerate(items):
                    res_dict['RenderedSpectra'][i] = self._xml_to_dict(item)

        return res_dict#self._xml_to_dict(data)

    def _xml_to_dict(self, data):
        full_res = {}
        for attr in data.items():
            ET.SubElement(data, attr[0])
            data.find(attr[0]).text = attr[1]
        if len(list(data)) == 0:
            if '64' in data.tag:
                return self.decode_bs64(data.text)
            else:
                return data.text
        for items in data:
            attr = self._return_layer_attr(items)  # return_child_dict(items)
            if attr:
                full_res.update(attr)
            if items.tag is not None:
                el1 = self._xml_to_dict(items)
                full_res[items.tag] = el1

        return full_res

    @staticmethod
    def decode_bs64(data):
        """Returns base64 data decoded in a numpy array"""
        if data is None:
            return np.ndarray(0)
        decoded_bytes = base64.b64decode(data.encode())
        fmt = 'f' * int((len(decoded_bytes) / 4))
        structured_data = struct.unpack(fmt, decoded_bytes)
        decoded_array = np.array(structured_data)
        return decoded_array

    @staticmethod
    def _return_layer_attr(el_tree):
        if len(el_tree.items()) > 0:
            res = {}
            for elem in el_tree.items():
                res[elem[0]] = elem[1]
            return res
        else:
            return None

    def _read_image(self, obj):
        # Convert it to sidpy dataset object
        title = obj['Label']
        units = str(obj['UnitPrefix']) + str(obj['Units'])

        sizeX, sizeY = float(obj['Size']['X']), float(obj['Size']['Y'])
        resX, resY = int(obj['Resolution']['X']), int(obj['Resolution']['Y'])

        data = obj['SampleBase64'].reshape(resX,resY)

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

        for key in obj['Tags']:
            metadata[key] = obj['Tags'][key]

        excluded_keys = ['Tags', 'Visible','SampleBase64']

        for key in obj:
            if key not in excluded_keys:
                metadata[key] = obj[key]

        return metadata

    def _read_spectrum(self, obj):
        data   = obj['DataChannels']['SampleBase64']

        _start_wn = float(obj['StartWavenumber'])
        _end_wn = float(obj['EndWavenumber'])
        _datapoints = int(obj['DataPoints'])
        data_x = np.linspace(_start_wn, _end_wn, _datapoints)
        title = obj['Label']

        posX, posY = float(obj['Location']['X']), float(obj['Location']['Y'])

        data_set = sid.Dataset.from_array(data)
        data_set.title = title
        data_set.data_type = 'spectrum'
        data_set.quantity = 'intensity'
        data_set.units = 'a.u.'

        data_set.set_dimension(0, sid.Dimension(data_x, 'wavenumber'))
        data_set.dim_0.dimension_type = 'spectral'
        data_set.dim_0.quantity = 'wavenumber'
        data_set.dim_0.units = 'cm-1'#?

        data_set.metadata = self._spectrum_metadata(obj)
        return data_set

    def _spectrum_metadata(self, obj):
        metadata = {}
        excluded_keys = ['Visible',
                         '{http://www.w3.org/2001/XMLSchema-instance}nil',
                         'DataChannels',
                         'Polarization',
                         'DutyCycle',
                         'PulseRate']

        for key in obj:
            if key not in excluded_keys:
                metadata[key] = obj[key]

        return metadata