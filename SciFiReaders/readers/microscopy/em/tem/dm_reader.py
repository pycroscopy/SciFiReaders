"""
Part of SciFiReaders, a pycroscopy module
Author: Gerd Duscher
################################################################################
# Python class for reading GATAN DM3/DM4 (DigitalMicrograph) files
# and extracting all metadata
# --
# tested on EELS spectra, spectrum images and single-image files and image-stacks
# --
# based on the DM3_Reader plug-in (v 1.3.4) for ImageJ by Greg Jefferis <jefferis@stanford.edu>
# http://rsb.info.nih.gov/ij/plugins/DM3_Reader.html
# --
# Python adaptation: Pierre-Ivan Raynal <raynal@med.univ-tours.fr>
# http://microscopies.med.univ-tours.fr/
#
# Extended for EELS support by Gerd Duscher, UTK 2012
# Rewritten for integration of sidpy 2020
# Rewritten for added support of DM4 2021
#    gleaned some ideas from https://github.com/jamesra/dm4reader
# Works for python 3
#
################################################################################
"""

from __future__ import division, print_function, absolute_import, unicode_literals
import os
import struct
import time
import warnings

import numpy as np

import sidpy

__version__ = '0.1beta'

DM4DataTypeDict = {2: {'num_bytes': 2, 'signed': True, 'type_format': 'h'},
                   3: {'num_bytes': 4, 'signed': True, 'type_format': 'i'},
                   4: {'num_bytes': 2, 'signed': False, 'type_format': 'H'},
                   5: {'num_bytes': 4, 'signed': False, 'type_format': 'I'},
                   6: {'num_bytes': 4, 'signed': True, 'type_format': 'f'},
                   # 8byte float
                   7: {'num_bytes': 8, 'signed': True, 'type_format': 'd'},
                   8: {'num_bytes': 1, 'signed': False, 'type_format': 'B'},
                   9: {'num_bytes': 1, 'signed': False, 'type_format': 'c'},
                   10: {'num_bytes': 1, 'signed': True, 'type_format': 'b'},
                   # 8 bit long-long for DM4
                   11: {'num_bytes': 8, 'signed': True, 'type_format': 'q'},
                   12: {'num_bytes': 8, 'signed': False, 'type_format': 'Q'}
                   }


# Utility functions
def read_header_dm(dm_file):
    """Read the header of a DM3/DM4 file."""
    dm_file.seek(0)
    # int.from_bytes(dm_file.read(4), byteorder='big')
    dm_version = struct.unpack_from('>I', dm_file.read(4))[0]
    if dm_version == 3:
        file_size = struct.unpack_from('>I', dm_file.read(8))[0]
        dm_header_size = 4 + 4 + 4
    elif dm_version == 4:
        file_size = struct.unpack_from('>Q', dm_file.read(8))[0]
        dm_header_size = 4 + 8 + 4
    else:
        raise TypeError('This is not a DM3 or DM4 File')
    byteorder = struct.unpack_from('>I', dm_file.read(4))[0]
    if byteorder == 1:
        endian = '>'  # little nedian
    else:
        endian = '<'  # big endian

    if dm_version == 4:  # not sure why
        if endian == '<':
            endian = '>'
        else:
            endian = '<'
    return dm_version, file_size, endian, dm_header_size


def _read_tag_name(dm_file):
    """Read the name of a tag from the DM file."""
    # DM specifies this property as always big endian
    tag_name_len = struct.unpack_from('>H', dm_file.read(2))[0]

    tag_name = '0'
    if tag_name_len > 0:
        data = dm_file.read(tag_name_len)
        try:
            tag_name = data.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            tag_name = None

    return tag_name


def _read_tag_garbage_str(dm_file):
    """
    DM4 has four bytes of % symbols in the tag.  Ensure it is there.
    """
    garbage_str = dm_file.read(4).decode('utf-8')
    assert garbage_str == '%%%%'


def _read_tag_data_info(dm_file, dm_version):
    if dm_version == 3:
        tag_array_length = struct.unpack('>l', dm_file.read(4))[0]
        format_str = '>' + tag_array_length * 'l'  # Big endian signed long
        tag_array_types = struct.unpack_from(format_str, dm_file.read(4 * tag_array_length))
    else:
        tag_array_length = struct.unpack_from('>Q', dm_file.read(8))[0]
        # DM4 specifies this property as always big endian
        format_str = '>' + tag_array_length * 'q'  # Big endian signed long

        tag_array_types = struct.unpack_from(format_str, dm_file.read(8 * tag_array_length))

    return tag_array_types


def read_string(dm_file, length=1):
    """Read len bytes as a string in file f"""
    read_bytes = dm_file.read(length)
    str_fmt = '>' + str(length) + 's'
    return struct.unpack(str_fmt, read_bytes)[0]


class DMReader(sidpy.Reader):
    """
    Reader of Digital Micrograph image and spectroscopy data

    This reader reads (attribute read) all the different data in the file and
    returns it as a dictionary 
    of sidpy.Datasets

    Parameter:
    ---------
    file_path: str
        filepath to dm3 or dm4 file.

    Return:
    ------
    datasets: dict
        dictionary of sidpy datasets
    """
    def __init__(self, file_path, verbose=False):
        super().__init__(file_path)

        # initialize variables ##
        self.verbose = verbose
        self.__filename = file_path
        self.datasets = {}
        self.spectral_dim = False

        # - open file for reading
        try:
            self.__dm_file = open(self.__filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        # - create Tags repositories
        self.__stored_tags = {'DM': {}}

        self.dm_version, self.file_size, self.endian, self.dm_header_size = read_header_dm(self.__dm_file)

        if self.verbose:
            print("Header info.:")
            print("- file version:", self.dm_version)
            print("- little endian:", self.endian)
            print("- file size:", self.file_size, "bytes")

        # don't read but close file
        self.close()

    def close(self):
        """Close the DM file."""
        self.__dm_file.close()

    def can_read(self):
        return self.dm_version in {3, 4}

    def read(self):
        """Read the DM file and extract metadata."""
        try:
            self.__dm_file = open(self.__filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        t1 = time.time()
        self.__dm_file.seek(self.dm_header_size)

        self.__stored_tags = {'DM': {'dm_version': self.dm_version, 'file_size': self.file_size},
                              'original_filename': self.filename}

        self.__read_tag_group(self.__stored_tags)

        if self.verbose:
            print(f"-- {len(self.__stored_tags)} Tags read --")

        if self.verbose:
            t2 = time.time()
            print(f"| parse DM3 file: {t2 - t1:.3g} s")
        start = 0
        if '1' in self.__stored_tags['ImageList']:
            start=1
        channel_number = 0
        for image_number in self.__stored_tags['ImageList'].keys():
            if int(image_number) >= start:
                dataset = self.get_dataset(self.__stored_tags['ImageList'][image_number])
                if isinstance(dataset, sidpy.Dataset):
                    dataset.original_metadata['DM'] = self.__stored_tags['DM']
                    # convert linescan to spectral image
                    if self.spectral_dim and dataset.ndim == 2:
                        old_dataset = dataset.copy()
                        meta = dataset.original_metadata.copy()
                        basename = dataset.name
                        data = np.array(dataset).reshape(dataset.shape[0], 1, dataset.shape[1])
                        dataset = sidpy.Dataset.from_array(data, name=basename)
                        dataset.original_metadata = meta
                        dataset.set_dimension(0, old_dataset.dim_0)

                        dataset.set_dimension(1, sidpy.Dimension([1], name='y', units='pixels',
                                                                 quantity='distance',
                                                                 dimension_type='spatial'))
                        dataset.set_dimension(2, old_dataset.dim_1)
                        dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE  # 'linescan'

                    dataset.quantity = 'intensity'
                    dataset.units = 'counts'
                    # dataset.title = basename
                    dataset.modality = 'generic'
                    dataset.source = 'SciFiReaders.DMReader'
                    dataset.original_metadata['DM']['full_file_name'] = self.__filename

                    key = f"Channel_{int(channel_number):03d}"
                    channel_number += 1
                    self.datasets[key] = dataset
                    self.extract_crucial_metadata(key)

        del self.__stored_tags['ImageList']
        main_dataset_key = list(self.datasets.keys())[0]

        for key, dataset in self.datasets.items():
            if 'urvey' in dataset.title:
                main_dataset_key = key
        if self.verbose:
            print(main_dataset_key)
        self.datasets[main_dataset_key].original_metadata.update(self.__stored_tags)
        self.close()
        return self.datasets

    def get_dataset(self, image_dict)->sidpy.Dataset:
        """
        Reads dictionary of imageList into sidpy.Dataset 
        """
        dataset = None
        _, file_name = os.path.split(self.__filename)
        basename, _ = os.path.splitext(file_name)
        if image_dict.get('ImageData', {}).get('Data', {}):
            dataset = sidpy.Dataset.from_array(self.get_raw(image_dict), name=basename)
            dataset.title = image_dict['Name']
            dataset.original_metadata = image_dict.copy()
            self.set_dimensions(dataset)
            self.set_data_type(dataset)
        return dataset

    def set_data_type(self, dataset):
        """Sets the data type of the dataset based on its shape and metadata."""
        self.spectral_dim = spectral_dim = len(dataset.get_spectral_dims()) > 0

        dataset.data_type = 'unknown'
        if dataset.original_metadata.get('ImageTags', {}).get('SI', {}):
            if len(dataset.shape) == 3:
                dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE
            else:
                if spectral_dim:
                    dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE  # 'linescan'
                else:
                    dataset.data_type = sidpy.DataType.IMAGE
                    dataset.metadata['image_type'] = 'survey image'

        if dataset.data_type == sidpy.DataType.UNKNOWN:
            if len(dataset.shape) > 3:
                raise NotImplementedError('Data_type not implemented yet')
            if len(dataset.shape) == 3:
                if spectral_dim:
                    dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE
                else:
                    dataset.data_type = 'image_stack'
            elif len(dataset.shape) == 2:
                if spectral_dim:
                    # basename = dataset.name
                    dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE
                else:
                    dataset.data_type = 'image'
            elif len(dataset.shape) == 1:
                if spectral_dim:
                    dataset.data_type = sidpy.DataType.SPECTRUM
                else:
                    dataset.data_type = sidpy.DataType.LINE_PLOT

    def set_dimensions(self, dataset):
        """Sets the dimensions of the dataset."""
        dimensions_dict = dataset.original_metadata.get('ImageData', {}).get('Calibrations', {})
        dimensions_dict = dimensions_dict.get('Dimension', {})
        reciprocal_name = 'u'
        spatial_name = 'x'

        for dim, dimension_tags in dimensions_dict.items():
            # Fix annoying scale of spectrum_images in Zeiss  and SEM images
            if dimension_tags['Units'] == '�m':
                dimension_tags['Units'] = 'nm'
                dimension_tags['Scale'] *= 1000.0

            if dimension_tags['Units'].strip() == '':
                units = 'counts'
            else:
                units = dimension_tags['Units']

            values = np.arange(dataset.shape[int(dim)]) - dimension_tags['Origin']
            values *= dimension_tags['Scale']

            if 'eV' == units:
                dataset.set_dimension(int(dim),
                                      sidpy.Dimension(values, name='energy_loss',
                                                      units=units, quantity='energy-loss',
                                                      dimension_type=sidpy.DimensionType.SPECTRAL))
            elif 'eV' in units:
                dataset.set_dimension(int(dim),
                                      sidpy.Dimension(values, name='energy',
                                                      units=units, quantity='energy',
                                                      dimension_type=sidpy.DimensionType.SPECTRAL))
            elif '1/' in units or units in ['mrad', 'rad']:
                dataset.set_dimension(int(dim),
                                      sidpy.Dimension(values, name=reciprocal_name,
                                                      units=units, quantity='reciprocal distance',
                                                      dimension_type=sidpy.DimensionType.RECIPROCAL))
                reciprocal_name = chr(ord(reciprocal_name) + 1)
            elif 'm' in units:
                dataset.set_dimension(int(dim),
                                      sidpy.Dimension(values, name=spatial_name, units=units,
                                                      quantity='distance',
                                                      dimension_type=sidpy.DimensionType.SPATIAL))
                spatial_name = chr(ord(spatial_name) + 1)
            else:
                units = 'frame'
                dataset.set_dimension(int(dim),
                                      sidpy.Dimension(values, name=spatial_name,
                                                      units=units, quantity='number',
                                                      dimension_type=sidpy.DimensionType.TEMPORAL))
                spatial_name = chr(ord(spatial_name) + 1)

        # For ill defined DM data
        if dataset.data_type.name == 'IMAGE':
            dataset.x.dimension_type = 'SPATIAL'
            dataset.y.dimension_type = 'SPATIAL'

    # utility functions

    def __read_tag_group(self, tags):
        """Reads a group of tags from the DM file."""
        _ = struct.unpack_from(self.endian + 'b', self.__dm_file.read(1))[0]
        _ = struct.unpack_from(self.endian + 'b', self.__dm_file.read(1))[0]

        if self.dm_version == 3:
            # this property is always big endian
            num_tags = struct.unpack_from('>l', self.__dm_file.read(4))[0]
        else:
             # this property is always big endian
            num_tags = struct.unpack_from('>Q', self.__dm_file.read(8))[0]

        # read Tags
        for _ in range(num_tags):
            tag_type = struct.unpack_from(self.endian + 'B', self.__dm_file.read(1))[0]
            is_data = tag_type == 21

            tag_label = _read_tag_name(self.__dm_file)
            if self.dm_version == 4:
                _ = struct.unpack_from('>Q', self.__dm_file.read(8))[0]
            if tag_label == '0':
                for key in tags:
                    if key.isdigit():
                        tag_label = str(int(key) + 1)

            if is_data:
                value = self.__read_any_data()
                tags[tag_label] = value
            else:
                tags[tag_label] = {}
                self.__read_tag_group(tags[tag_label])
        return 1

    def __read_any_data(self):
        """Reads any data from the DM file."""
        _read_tag_garbage_str(self.__dm_file)
        tag_array_types = _read_tag_data_info(self.__dm_file, self.dm_version)
        encoded_type = tag_array_types[0]

        if encoded_type < 13:
            data = self.__read_native_data(encoded_type)
        elif encoded_type == 18:  # STRING
            data = self.__read_string_data(tag_array_types[1])
        elif encoded_type == 15:  # STRUCT:
            data = self.__read_struct_data(tag_array_types)
        elif encoded_type == 20:  # ARRAY:
            if tag_array_types[1] == 15:
                data = []
                for _ in range(tag_array_types[-1]):
                    data.append(self.__read_struct_data(tag_array_types[1:]))
            elif tag_array_types[1] == 20:
                data = self.__read_array_data(tag_array_types[1:])
            else:
                data = self.__read_array_data(tag_array_types)
        else:
            out_error = "rAnD, " + str(self.__dm_file.tell()) + ": Can't understand encoded type"
            raise ValueError(out_error)
        return data

    def __read_native_data(self, encoded_type):
        """Reads native data from the DM file."""
        if encoded_type in DM4DataTypeDict:
            data_type = DM4DataTypeDict[encoded_type]
            format_str = self.endian + data_type['type_format']
            byte_data = self.__dm_file.read(data_type['num_bytes'])
            val = struct.unpack_from(format_str, byte_data)[0]
        else:
            out_error = "rND, " + hex(self.__dm_file.tell()) + ": Unknown data type " + str(encoded_type)
            raise ValueError(out_error)
        return val

    def __read_string_data(self, string_size):
        """Reads string data from the DM file."""
        if string_size <= 0:
            r_string = ""
        else:
            # !!! *Unicode* string (UTF-16)... convert to Python unicode str
            r_string = read_string(self.__dm_file, string_size)
            r_string = str(r_string, "utf_16_le")
        return r_string

    def __read_array_data(self, array_types):
        """Reads array data from the DM file."""
        array_size = array_types[-1]
        item_size = 0
        encoded_type = 0
        for i in range(len(array_types)-2):
            encoded_type = int(array_types[i+1])
            et_size = DM4DataTypeDict[encoded_type]['num_bytes']
            item_size += et_size
        buf_size = array_size * item_size

        if len(array_types)-2 == 1 and encoded_type == 4 and array_size < 256:
            # treat as string
            val = self.__read_string_data(buf_size)
        else:
            # treat as binary data
            # - store data size and offset as tags
            val = self.__dm_file.read(buf_size)
        return val

    def __read_struct_data(self, struct_types):
        """Reads struct data from the DM file."""
        data = []
        for encoded_type in struct_types[4::2]:
            data.append(self.__read_native_data(encoded_type))
        return data

    # ## END utility functions ###

    def get_filename(self):
        """Gets the filename of the DM file."""
        return self.__filename

    filename = property(get_filename)

    def get_tags(self):
        """Gets the tags from the DM file."""
        return self.__stored_tags

    tags = property(get_tags)

    def get_raw(self, image_dict):
        """Extracts  data as np array"""

        # DataTypes for image data <--> PIL decoders
        data_types = {
            1: '<u2',  # 2 byte integer signed ("short")
            2: '<f4',  # 4 byte real (IEEE 754)
            3: '<c8',  # 8 byte complex (real, imaginary)
            4: '',  # ?
            # 4 byte packed complex (see below)
            5: (np.int16, {'real': (np.int8, 0), 'imaginary': (np.int8, 1)}),
            6: '<u1',  # 1 byte integer unsigned ("byte")
            7: '<i4',  # 4 byte integer signed ("long")
            # I do not have any dm3 file with this format to test it.
            8: '',  # rgb view, 4 bytes/pixel, unused, red, green, blue?
            9: '<i1',  # byte integer signed
            10: '<u2',  # 2 byte integer unsigned
            11: '<u4',  # 4 byte integer unsigned
            12: '<f8',  # 8 byte real
            13: '<c16',  # byte complex
            14: 'bool',  # 1 byte binary (ie 0 or 1)
            # Packed RGB. It must be a recent addition to the format because it does
            # not appear in http://www.microscopy.cen.dtu.dk/~cbb/info/dmformat/
            23: (np.float32, {'R': ('<u1', 0), 'G': ('<u1', 1), 'B': ('<u1', 2), 'A': ('<u1', 3)}),
        }

        # get relevant Tags
        byte_data = image_dict['ImageData']['Data']
        data_type = image_dict['ImageData']['DataType']
        dimensions = image_dict['ImageData']['Dimensions']

        # get shape from Dimensions
        shape = []
        for dim in dimensions:
            shape.append(dimensions[dim])

        # get data_type and reformat into numpy array
        dt = data_types[data_type]
        if dt == '':
            raise TypeError('The datatype is not supported')
        raw_data = np.frombuffer(byte_data, dtype=dt, 
                                 count=np.cumprod(shape)[-1]).reshape(shape, order='F')
        # delete byte data in dictionary
        image_dict['ImageData']['Data'] = 'read'
        return raw_data

    def extract_crucial_metadata(self, dataset_key):
        """Extracts crucial metadata from the original_metadata dictionary."""
        original_metadata = self.datasets[dataset_key].original_metadata
        if not isinstance(original_metadata, dict):
            raise TypeError('We need a dictionary to read')
        experiment = {}
        if not original_metadata.get('DM', {}):
            return experiment
        if 'ImageTags' not in original_metadata:
            return experiment
        exp_dictionary = original_metadata.get('ImageTags', {})

        tag = exp_dictionary.get('EELS', {}).get('Acquisition', {}).get('Exposure (s)', 0.)
        experiment['single_exposure_time'] = tag
        tag = exp_dictionary.get('EELS', {}).get('Integration', {}).get('Integration (s)', -1)
        experiment['exposure_time'] = tag
        for key, item in exp_dictionary.get('EELS', {}).get('Acquisition', {}).items():
            if 'frames' in key:
                experiment['number_of_frames'] = item
                print('frames: ',key)
        exp_dictionary = original_metadata.get('ImageTags', {}).get('EELS', {})
        exp_dictionary = exp_dictionary.get('Experimental Conditions', {})
        experiment['convergence_angle'] = exp_dictionary.get('Convergence Angle', 0.)
        experiment['collection_angle'] = exp_dictionary.get('Collection Angle', 0.)
        experiment['number_of_frames'] = experiment.get('number_of_frames', 1)
        if 'exposure_time' not in experiment:
            experiment['exposure_time'] = experiment.get('number_of_frames', 1) \
                                        * experiment.get('single_exposure_time', -1)
        if experiment['exposure_time'] < 0:
            exp_dictionary = original_metadata.get('ImageTags', {}).get('Acquisition', {})
            exp_dictionary = exp_dictionary.get('Parameters', {}).get('High Level', {})
            experiment['exposure_time'] = exp_dictionary.get('Exposure (s)', 0)

        exp_dictionary = original_metadata.get('ImageTags', {}).get('Microscope Info', {})
        experiment['microscope'] = exp_dictionary.get('Microscope', 'Unknown')
        experiment['acceleration_voltage'] = exp_dictionary.get('Voltage', None)

        self.datasets[dataset_key].metadata['experiment']  = experiment
        return experiment

class DM3Reader(DMReader):
    """
    DM3 file reader class.
    """
    def __init__(self, file_path, verbose=False):

        warnings.warn(DeprecationWarning('Use DMReader class instead marking\n '
                                         'Note that you can now read dm4 files too'))
        super().__init__(file_path, verbose=verbose)

    def can_read(self):
        return self.dm_version == 3
