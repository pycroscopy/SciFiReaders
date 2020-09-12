#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

################################################################################
# Python class for reading GATAN DM3 (DigitalMicrograph) files
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
#
# Works for python 3
#
################################################################################
from __future__ import division, print_function, absolute_import, unicode_literals

import struct
import time
import numpy

from warnings import warn
import sys
import numpy as np
import os

from sidpy import Reader
from sidpy.sid import Dimension, Dataset
from sidpy.base.dict_utils import nest_dict

__all__ = ["DM3Reader", "version"]

version = '0.1beta'

debugLevel = 0  # 0=none, 1-3=basic, 4-5=simple, 6-10 verbose

if sys.version_info.major == 3:
    unicode = str

# ### utility functions ###

# ## binary data reading functions ###


def read_long(f):
    """Read 4 bytes as integer in file f"""
    read_bytes = f.read(4)
    return struct.unpack('>l', read_bytes)[0]


def read_short(f):
    """Read 2 bytes as integer in file f"""
    read_bytes = f.read(2)
    return struct.unpack('>h', read_bytes)[0]


def read_byte(f):
    """Read 1 byte as integer in file f"""
    read_bytes = f.read(1)
    return struct.unpack('>b', read_bytes)[0]


def read_bool(f):
    """Read 1 byte as boolean in file f"""
    read_val = read_byte(f)
    return read_val != 0


def read_char(f):
    """Read 1 byte as char in file f"""
    read_bytes = f.read(1)
    return struct.unpack('c', read_bytes)[0]


def read_string(f, length=1):
    """Read len bytes as a string in file f"""
    read_bytes = f.read(length)
    str_fmt = '>' + str(length) + 's'
    return struct.unpack(str_fmt, read_bytes)[0]


def read_le_short(f):
    """Read 2 bytes as *little endian* integer in file f"""
    read_bytes = f.read(2)
    return struct.unpack('<h', read_bytes)[0]


def read_le_long(f):
    """Read 4 bytes as *little endian* integer in file f"""
    read_bytes = f.read(4)
    return struct.unpack('<l', read_bytes)[0]


def read_leu_short(f):
    """Read 2 bytes as *little endian* unsigned integer in file f"""
    read_bytes = f.read(2)
    return struct.unpack('<H', read_bytes)[0]


def read_leu_long(f):
    """Read 4 bytes as *little endian* unsigned integer in file f"""
    read_bytes = f.read(4)
    return struct.unpack('<L', read_bytes)[0]


def read_leu_float(f):
    """Read 4 bytes as *little endian* float in file f"""
    read_bytes = f.read(4)
    return struct.unpack('<f', read_bytes)[0]


def read_leu_double(f):
    """Read 8 bytes as *little endian* double in file f"""
    read_bytes = f.read(8)
    return struct.unpack('<d', read_bytes)[0]


# constants for encoded data types ##
SHORT = 2
LONG = 3
USHORT = 4
ULONG = 5
FLOAT = 6
DOUBLE = 7
BOOLEAN = 8
CHAR = 9
OCTET = 10
STRUCT = 15
STRING = 18
ARRAY = 20

# - association data type <--> reading function
readFunc = {
    SHORT: read_le_short,
    LONG: read_le_long,
    USHORT: read_leu_short,
    ULONG: read_leu_long,
    FLOAT: read_leu_float,
    DOUBLE: read_leu_double,
    BOOLEAN: read_bool,
    CHAR: read_char,
    OCTET: read_char,  # difference with char???
}

# other constants ##
IMGLIST = "root.ImageList."
OBJLIST = "root.DocumentObjectList."
MAXDEPTH = 64


# END constants ##


class DM3Reader(Reader):
    debugLevel = -1

    def __init__(self, file_path, verbose=False):
        """
        file_path: filepath to dm3 file.
        """
        super(DM3Reader, self).__init__(file_path)

        # initialize variables ##
        self.verbose = verbose
        self.__chosenImage = 1
        # - track currently read group
        self.__cur_group_level = -1
        self.__cur_group_at_level_x = [0 for x in range(MAXDEPTH)]
        self.__cur_group_name_at_level_x = ['' for x in range(MAXDEPTH)]
        # - track current tag
        self.__cur_tag_at_level_x = ['' for x in range(MAXDEPTH)]
        self.__curTagName = ''
        # - open file for reading
        try:
            self.__f = open(self._input_file_path, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        # - create Tags repositories
        self.__storedTags = []
        self.__tagDict = {'DM': {}}

        # check if this is valid DM3 file
        is_dm3 = True
        # read header (first 3 4-byte int)
        # get version
        file_version = read_long(self.__f)
        if file_version not in (3, 4):
            is_dm3 = False
        # get indicated file size
        file_size = read_long(self.__f)
        # get byte-ordering
        le = read_long(self.__f)
        little_endian = (le == 1)
        if not little_endian:
            is_dm3 = False
        # check file header, raise Exception if not DM3
        if not is_dm3:
            raise TypeError("%s does not appear to be a DM3 or DM4 file." % os.path.split(self._input_file_path)[1])
        elif self.verbose:
            print("%s appears to be a DM3 file" % self._input_file_path)
        self.file_version = file_version
        self.file_size = file_size

        if self.verbose:
            print("Header info.:")
            print("- file version:", file_version)
            print("- le:", le)
            print("- file size:", file_size, "bytes")

        # set name of root group (contains all data)...
        self.__cur_group_name_at_level_x[0] = "root"
        # ... then read it
        self.__f.close()

    def can_read(self):
        """
        Tests whether or not the provided file has a .dm3 extension
        Returns
        -------

        """
        # TODO: @gduscher to elaborate if this is not a sufficient check
        return super(DM3Reader, self).can_read(extension='dm3')

    def read(self):
        """
        Extracts data and metadata present in the provided file

        Returns
        -------
        dataset : sidpy.Dataset
            Dataset object containing the data and metadata
        """
        t1 = time.time()
        try:
            self.__f = open(self._input_file_path, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        file_version = read_long(self.__f)
        file_size = read_long(self.__f)
        le = read_long(self.__f)
        little_endian = (le == 1)
        # ... then read it
        self.__read_tag_group()

        if self.verbose:
            print("-- %s Tags read --" % len(self.__storedTags))

        if self.verbose:
            t2 = time.time()
            print("| parse DM3 file: %.3g s" % (t2 - t1))

        dataset = Dataset.from_array(self.data_cube)
        original_tags = nest_dict(self.get_tags(), separator='.')
        dataset.original_metadata.update(original_tags['root'])

        dataset.quantity = 'intensity'
        dataset.units = 'counts'
        self.set_dimensions(dataset)

        self.set_data_type(dataset)

        path, file_name = os.path.split(self._input_file_path)
        basename, extension = os.path.splitext(file_name)
        dataset.title = basename

        dataset.modality = 'generic'
        dataset.source = 'DM3Reader'

        return dataset

    def set_data_type(self, dataset):
        image_number = len(dataset.original_metadata['ImageList']) - 1
        spectral_dim = False
        for axis in dataset.axes.values():
            if axis.dimension_type == 'spectral':
                spectral_dim = True

        dataset.data_type = 'unknown'
        if 'ImageTags' in dataset.original_metadata['ImageList'][str(image_number)]:
            image_tags = dataset.original_metadata['ImageList'][str(image_number)]['ImageTags']

            if 'SI' in image_tags:
                if len(dataset.shape) == 3:
                    dataset.data_type = 'spectrum_image'
                else:
                    if spectral_dim:
                        dataset.data_type = 'spectrum_image'  # 'linescan'
                    else:
                        dataset.data_type = 'image'
                        dataset.metadata['image_type'] = 'survey image'

        if dataset.data_type == 'unknown':
            if len(dataset.shape) > 3:
                raise NotImplementedError('Data_type not implemented yet')
            elif len(dataset.shape) == 3:
                if spectral_dim:
                    dataset.data_type = 'spectrum_image'
                else:
                    dataset.data_type = 'image_stack'
            elif len(dataset.shape) == 2:
                if spectral_dim:
                    dataset.data_type = 'spectrum_image'
                else:
                    dataset.data_type = 'image'
            elif len(dataset.shape) == 1:
                if spectral_dim:
                    dataset.data_type = 'spectrum'
                else:
                    dataset.data_type = 'line_plot'

    def set_dimensions(self, dataset):
        image_number = len(dataset.original_metadata['ImageList']) - 1
        dimensions_dict = dataset.original_metadata['ImageList'][str(image_number)]['ImageData']['Calibrations']['Dimension']

        reciprocal_name = 'u'
        spatial_name = 'x'

        for dim, dimension_tags in dimensions_dict.items():
            # Fix annoying scale of spectrum_images in Zeiss  and SEM images
            if dimension_tags['Units'] == 'µm':
                dimension_tags['Units'] = 'nm'
                dimension_tags['Scale'] *= 1000.0

            units = dimension_tags['Units']
            values = (np.arange(dataset.shape[int(dim)]) - dimension_tags['Origin']) * dimension_tags['Scale']

            if 'eV' == units:
                dataset.set_dimension(int(dim), Dimension('energy_loss', values, units=units,
                                                          quantity='energy-loss', dimension_type='spectral'))
            elif 'eV' in units:
                dataset.set_dimension(int(dim), Dimension('energy', values, units=units,
                                                          quantity='energy', dimension_type='spectral'))
            elif '1/' in units or units in ['mrad', 'rad']:
                dataset.set_dimension(int(dim), Dimension(reciprocal_name, values, units=units,
                                                          quantity='reciprocal distance', dimension_type='reciprocal'))
                reciprocal_name = chr(ord(reciprocal_name) + 1)
            else:
                dataset.set_dimension(int(dim), Dimension(spatial_name, values, units=units,
                                                          quantity='distance', dimension_type='spatial'))
                spatial_name = chr(ord(spatial_name) + 1)

    # utility functions
    def __make_group_string(self):
        t_string = self.__cur_group_at_level_x[0]
        for i in range(1, self.__cur_group_level + 1):
            t_string += '.' + self.__cur_group_at_level_x[i]
        return t_string

    def __make_group_name_string(self):
        t_string = self.__cur_group_name_at_level_x[0]
        for i in range(1, self.__cur_group_level + 1):
            t_string += '.' + str(self.__cur_group_name_at_level_x[i])
        return t_string

    def __read_tag_group(self):
        # go down a level
        self.__cur_group_level += 1
        # increment group counter
        self.__cur_group_at_level_x[self.__cur_group_level] += 1
        # set number of current tag to -1 --- readTagEntry() pre-increments => first gets 0
        self.__cur_tag_at_level_x[self.__cur_group_level] = -1
        # if ( debugLevel > 5):
        #       print "rTG: Current Group Level:", self.__cur_group_level
        # is the group sorted?
        g_sorted = read_byte(self.__f)
        is_sorted = (g_sorted == 1)
        # is the group open?
        opened = read_byte(self.__f)
        is_open = (opened == 1)
        # number of Tags
        n_tags = read_long(self.__f)
        # if ( debugLevel > 5):
        #       print "rTG: Iterating over the", n_tags, "tag entries in this group"
        # read Tags
        for i in range(n_tags):
            self.__read_rag_entry()
        # go back up one level as reading group is finished
        self.__cur_group_level += -1
        return 1

    def __read_rag_entry(self):
        # is data or a new group?
        data = read_byte(self.__f)
        is_data = (data == 21)
        self.__cur_tag_at_level_x[self.__cur_group_level] += 1
        # get tag label if exists
        len_tag_label = read_short(self.__f)
        if len_tag_label != 0:
            tag_label = read_string(self.__f, len_tag_label).decode('latin-1')
            # print(tag_label)
        else:
            tag_label = str(self.__cur_tag_at_level_x[self.__cur_group_level])
        # if ( debugLevel > 5):
        #       print str(self.__cur_group_level)+"|"+__make_group_string()+": Tag label = "+tag_label
        # elif ( debugLevel > 0 ):
        #       print str(self.__cur_group_level)+": Tag label = "+tag_label
        if is_data:
            # give it a name
            self.__curTagName = self.__make_group_name_string() + "." + tag_label  # .decode('utf8')
            # read it
            self.__read_tag_type()
        else:
            # it is a tag group
            self.__cur_group_name_at_level_x[self.__cur_group_level + 1] = tag_label
            self.__read_tag_group()  # increments curGroupLevel
        return 1

    def __read_tag_type(self):
        delim = read_string(self.__f, 4)
        if delim != b"%%%%":
            raise Exception(hex(self.__f.tell()) + ": Tag Type delimiter not %%%%")
        n_in_tag = read_long(self.__f)
        self.__read_any_data()
        return 1

    def __encoded_type_size(self, et):
        # returns the size in bytes of the data type
        if et == 0:
            width = 0
        elif et in (BOOLEAN, CHAR, OCTET):
            width = 1
        elif et in (SHORT, USHORT):
            width = 2
        elif et in (LONG, ULONG, FLOAT):
            width = 4
        elif et == DOUBLE:
            width = 8
        else:
            # returns -1 for unrecognised types
            width = -1
        return width

    def __read_any_data(self):
        # higher level function dispatching to handling data types to other functions
        # - get Type category (short, long, array...)
        encoded_type = read_long(self.__f)
        # - calc size of encoded_type
        et_size = self.__encoded_type_size(encoded_type)
        if debugLevel > 5:
            print(": Tag Type = " + str(encoded_type) + ", Tag Size = " + str(et_size))
        if et_size > 0:
            self.__store_tag(self.__curTagName, self.__read_native_data(encoded_type, et_size))
        elif encoded_type == STRING:
            string_size = read_long(self.__f)
            data = self.__read_string_data(string_size)
            if debugLevel > 5:
                print('String')
                print(data)
        elif encoded_type == STRUCT:
            # GD does  store tags  now
            struct_types = self.__read_struct_types()
            data = self.__read_struct_data(struct_types)
            # print('Struct ',self.__curTagName)
            if debugLevel > 5:
                print('Struct')
                print(data)
            self.__store_tag(self.__curTagName, data)

        elif encoded_type == ARRAY:
            # GD does  store tags now
            # indicates size of skipped data blocks
            array_types = self.__read_array_types()
            data = self.__read_array_data(array_types)
            # print('Array ',self.__curTagName)
            if debugLevel > 5:
                print('Array')
                print(data)
            self.__store_tag(self.__curTagName, data)

        else:
            raise Exception("rAnD, " + hex(self.__f.tell()) + ": Can't understand encoded type")
        return 1

    def __read_native_data(self, encoded_type, et_size):
        # reads ordinary data types
        if encoded_type in readFunc.keys():
            val = readFunc[encoded_type](self.__f)
        else:
            raise Exception("rND, " + hex(self.__f.tell()) + ": Unknown data type " + str(encoded_type))
        # if ( debugLevel > 3 ):
        #       print "rND, " + hex(self.__f.tell()) + ": " + str(val)
        # elif ( debugLevel > 0 ):
        #      print val
        return val

    def __read_string_data(self, string_size):
        # reads string data
        if string_size <= 0:
            r_string = ""
        else:
            # if ( debugLevel > 3 ):
            # print "rSD @ " + str(f.tell()) + "/" + hex(f.tell()) +" :",
            # !!! *Unicode* string (UTF-16)... convert to Python unicode str
            r_string = read_string(self.__f, string_size)
            r_string = str(r_string, "utf_16_le")
            # if ( debugLevel > 3 ):
            #       print r_string + "   <"  + repr( r_string ) + ">"
        # if ( debugLevel > 0 ):
        #       print "StringVal:", r_string
        self.__store_tag(self.__curTagName, r_string)
        return r_string

    def __read_array_types(self):
        # determines the data types in an array data type
        array_type = read_long(self.__f)
        item_types = []
        if array_type == STRUCT:
            item_types = self.__read_struct_types()
        elif array_type == ARRAY:
            item_types = self.__read_array_types()
        else:
            item_types.append(array_type)
        return item_types

    def __read_array_data(self, array_types):
        # reads array data

        array_size = read_long(self.__f)

        # if ( debugLevel > 3 ):
        #       print "rArD, " + hex( f.tell() ) + ": Reading array of size = " + str(array_size)

        item_size = 0
        encoded_type = 0

        for i in range(len(array_types)):
            encoded_type = int(array_types[i])
            et_size = self.__encoded_type_size(encoded_type)
            item_size += et_size
            # if ( debugLevel > 5 ):
            #       print "rArD: Tag Type = " + str(encoded_type) + ", Tag Size = " + str(et_size)
            # ! readNativeData( encoded_type, et_size ) !##

        # if ( debugLevel > 5 ):
        #       print "rArD: Array Item Size = " + str(item_size)

        buf_size = array_size * item_size

        if ((not self.__curTagName.endswith("ImageData.Data"))
                and (len(array_types) == 1)
                and (encoded_type == USHORT)
                and (array_size < 256)):
            # treat as string
            val = self.__read_string_data(buf_size)
        else:
            # treat as binary data
            # - store data size and offset as tags
            self.__store_tag(self.__curTagName + ".Size", buf_size)
            self.__store_tag(self.__curTagName + ".Offset", self.__f.tell())
            # - skip data w/o reading
            self.__f.seek(self.__f.tell() + buf_size)
            val = 1

        return val

    def __read_struct_types(self):
        # analyses data types in a struct

        # if ( debugLevel > 3 ):
        #       print "Reading Struct Types at Pos = " + hex(self.__f.tell())

        struct_name_length = read_long(self.__f)
        n_fields = read_long(self.__f)

        # if ( debugLevel > 5 ):
        #       print "n_fields = ", n_fields

        # if ( n_fields > 100 ):
        #       raise Exception, hex(self.__f.tell())+": Too many fields"

        field_types = []
        name_length = 0
        for i in range(n_fields):
            name_length = read_long(self.__f)
            # if ( debugLevel > 9 ):
            #       print i + "th namelength = " + nameLength
            field_type = read_long(self.__f)
            field_types.append(field_type)

        return field_types

    def __read_struct_data(self, struct_types):
        # reads struct data based on type info in structType
        data = []
        for i in range(len(struct_types)):
            encoded_type = struct_types[i]
            et_size = self.__encoded_type_size(encoded_type)

            # if ( debugLevel > 5 ):
            #       print "Tag Type = " + str(encoded_type) + ", Tag Size = " + str(et_size)

            # get data
            data.append(self.__read_native_data(encoded_type, et_size))

        return data

    def __store_tag(self, tag_name, tag_value):
        # NB: all tag values (and names) stored as unicode objects;
        #     => can then be easily converted to any encoding
        # - /!\ tag names may not be ascii char only (e.g. '\xb5', i.e. MICRO SIGN)
        tag_name = str(tag_name)  # , 'latin-1')

        # GD: Changed this over to store real values and not strings in dictionary
        self.__tagDict[tag_name] = tag_value
        # - convert tag value to unicode if not already unicode object (as for string data)
        tag_value = str(tag_value)
        # store Tags as list and dict
        self.__storedTags.append(tag_name + " = " + tag_value)

    # ## END utility functions ###

    def get_filename(self):
        return self._input_file_path

    filename = property(get_filename)

    def get_tags(self):
        return self.__tagDict

    tags = property(get_tags)

    def get_raw(self):
        """Extracts  data as np array"""

        # DataTypes for image data <--> PIL decoders
        data_types = {
            '1': '<u2',  # 2 byte integer signed ("short")
            '2': '<f4',  # 4 byte real (IEEE 754)
            '3': '<c8',  # 8 byte complex (real, imaginary)
            '4': '',  # ?
            # 4 byte packed complex (see below)
            '5': (numpy.int16, {'real': (numpy.int8, 0), 'imaginary': (numpy.int8, 1)}),
            '6': '<u1',  # 1 byte integer unsigned ("byte")
            '7': '<i4',  # 4 byte integer signed ("long")
            # I do not have any dm3 file with this format to test it.
            '8': '',  # rgb view, 4 bytes/pixel, unused, red, green, blue?
            '9': '<i1',  # byte integer signed
            '10': '<u2',  # 2 byte integer unsigned
            '11': '<u4',  # 4 byte integer unsigned
            '12': '<f8',  # 8 byte real
            '13': '<c16',  # byte complex
            '14': 'bool',  # 1 byte binary (ie 0 or 1)
            # Packed RGB. It must be a recent addition to the format because it does
            # not appear in http://www.microscopy.cen.dtu.dk/~cbb/info/dmformat/
            '23': (numpy.float32,
                   {'R': ('<u1', 0), 'G': ('<u1', 1), 'B': ('<u1', 2), 'A': ('<u1', 3)}),
        }
        # get relevant Tags

        data_dim = 0  # 1 = spectrum, 2 = image, 3 = SI
        image_root = 'root.ImageList.1.'

        if image_root + 'ImageData.Data.Offset' in self.tags:
            data_offset = int(self.tags[image_root + 'ImageData.Data.Offset'])
        elif 'root.ImageList.0.ImageData.Data.Offset' in self.tags:
            image_root = 'root.ImageList.0.'
            data_offset = int(self.tags[image_root + 'ImageData.Data.Offset'])
            print('not original image')
        else:
            print('no offset')
        im_width = 0
        if image_root + 'ImageData.Data.Size' in self.tags:
            data_size = int(self.tags[image_root + 'ImageData.Data.Size'])
        if image_root + 'ImageData.Data.DataType' in self.tags:
            data_type = int(self.tags[image_root + 'ImageData.DataType'])
        if image_root + 'ImageData.Dimensions.0' in self.tags:
            im_width = int(self.tags[image_root + 'ImageData.Dimensions.0'])
        if image_root + 'ImageData.Dimensions.1' in self.tags:
            im_height = int(self.tags[image_root + 'ImageData.Dimensions.1'])
            data_dim = 2
        else:
            # print("Notice: spectrum data with spectrum length %s channels " % im_width)
            im_height = 1
            data_dim = 1
        if image_root + 'ImageData.Dimensions.2' in self.tags:
            im_length = int(self.tags[image_root + 'ImageData.Dimensions.2'])
            data_dim = 3

        if self.verbose:
            print("Notice: image data in %s starts at %s" % (os.path.split(self._input_file_path)[1], hex(data_offset)))
            print("Notice: image size: %sx%s px" % (im_width, im_height))

        # check if DataType is implemented, then read
        if image_root + 'ImageData.DataType' in self.tags:
            dt = data_types[str(self.tags[image_root + 'ImageData.DataType'])]
        else:
            dt = data_types[str(self.tags['root.ImageList.0.ImageData.DataType'])]
        if dt == '':
            print('The datatype is not supported')
            return
        # if data_type in dataTypes.keys():
        else:
            # decoder = dataTypes[data_type]
            # if self.debug>0:
            #       print "Notice: image data read as %s"%decoder
            #       t1 = time.time()

            self.__f.seek(data_offset)
            rawdata = self.__f.read(data_size)

            if data_dim > 2:
                # print rawdata[0],rawdata[1],rawdata[2],rawdata[3]
                shape = (im_width, im_height, im_length)
            else:
                shape = (im_width, im_height)
            if data_dim == 1:
                shape = im_width

            raw_data = numpy.fromstring(rawdata, dtype=dt, count=numpy.cumprod(shape)[-1]).reshape(shape, order='F')
            # raw_data = numpy.array(rawdata).reshape(im_width,im_height,im_length)
            # print raw_data[0],raw_data[1],raw_data[2],raw_data[3]#raw_data = numpy.array(rawdata).
            # reshape((im_width,im_height,im_length), order = 'F')
        return raw_data

    data_cube = property(get_raw)


if __name__ == '__main__':
    pass  # print "DM3lib v.%s"%version
