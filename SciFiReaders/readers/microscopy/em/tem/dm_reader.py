import struct
import time
import numpy

import sys
import numpy as np
import os

import sidpy

version = '0.1beta'


DM4DataTypeDict = {2: {'num_bytes': 2, 'signed': True, 'type_format': 'h'},
                   3: {'num_bytes': 4, 'signed': True, 'type_format': 'i'},
                   4: {'num_bytes': 2, 'signed': False, 'type_format': 'H'},
                   5: {'num_bytes': 4, 'signed': False, 'type_format': 'I'},
                   6: {'num_bytes': 4, 'signed': False, 'type_format': 'f'},
                   7: {'num_bytes': 8, 'signed': False, 'type_format': 'd'},  # 8byte float
                   8: {'num_bytes': 1, 'signed': False, 'type_format': '?'},
                   9: {'num_bytes': 2, 'signed': True, 'type_format': 'c'},
                   10: {'num_bytes': 2, 'signed': True, 'type_format': 'b'},
                   11: {'num_bytes': 8, 'signed': True, 'type_format': 'q'},
                   12: {'num_bytes': 8, 'signed': True, 'type_format': 'Q'}
                   }
def tag_is_directory(tag):
    return tag.type == 20

def read_header_dm(dmfile):
    dmfile.seek(0)
    version = struct.unpack_from('>I', dmfile.read(4))[0]  # int.from_bytes(dmfile.read(4), byteorder='big')
    if version == 3:
        file_size = struct.unpack_from('>I', dmfile.read(8))[0]
        DM_header_size = 4 + 4 + 4

    elif version == 4:
        file_size = struct.unpack_from('>Q', dmfile.read(8))[0]
        DM_header_size = 4 + 8 + 4

    else:
        raise TypeError('This is not a DM3 or DM4 File')
    byteorder = struct.unpack_from('>I', dmfile.read(4))[0]

    if byteorder == 1:
        endian = '>'
    else:
        endian = '<'

    return version, file_size, endian, DM_header_size


def read_tag_dir_header_dm(dmfile, endian, dm_version):
    """
    Read the root directory information from a dm file.
    """
    issorted = struct.unpack_from(endian + 'b', dmfile.read(1))[0]
    isclosed = struct.unpack_from(endian + 'b', dmfile.read(1))[0]
    if dm_version == 3:
        num_tags = struct.unpack_from('>l', dmfile.read(4))[0]  # DM4 specifies this property as always big endian
    else:
        num_tags = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian

    return issorted, isclosed, num_tags


def _read_tag_name(dmfile, endian):
    tag_name_len = struct.unpack_from('>H', dmfile.read(2))[0]  # DM4 specifies this property as always big endian
    tag_name = None
    if tag_name_len > 0:
        data = dmfile.read(tag_name_len)
        try:
            tag_name = data.decode('utf-8', errors='ignore')
        except UnicodeDecodeError as e:
            tag_name = None

    return tag_name


def _read_tag_garbage_str(dmfile):
    '''
    DM4 has four bytes of % symbols in the tag.  Ensure it is there.
    '''
    garbage_str = dmfile.read(4).decode('utf-8')
    assert (garbage_str == '%%%%')


def _read_tag_data_info(dmfile):
    #tag_array_length = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian
    format_str = '>' + tag_array_length * 'q'  # Big endian signed long

    tag_array_types = struct.unpack_from(format_str, dmfile.read(8 * tag_array_length))

    return (tag_array_length, tag_array_types)


def _read_tag_data(dmfile, endian):
    try:
        tag_byte_length = struct.unpack_from('<Q', dmfile.read(8))[0]
        # DM4 specifies this property as always big endian

        _read_tag_garbage_str(dmfile)
        (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

        tag_data_type_code = tag_array_types[0]

        if tag_data_type_code == 15:
            return read_tag_data_group(dmfile, endian)
        elif tag_data_type_code == 20:
            return read_tag_data_array(dmfile, endian)

        if not tag_data_type_code in DM4DataTypeDict:
            print("Missing type " + str(tag_data_type_code))
            return None

        return _read_tag_data_value(dmfile, endian, tag_data_type_code)

    finally:
        # Ensure we are in the correct position to read the next tag regardless of how reading this tag goes
        #  dmfile.seek(data_offset + tag.byte_length)
        pass


def read_tag_header_dm(dmfile, endian):
    '''Read the tag from the file.  Leaves file at the end of the tag data, ready to read the next tag from the file'''
    tag_type = struct.unpack_from(endian + 'B', dmfile.read(1))[0]
    if tag_type == 20:
        return _read_tag_dir_header_dm4(dmfile, endian)
    if tag_type == 0:
        return None

    tag_name = _read_tag_name(dmfile, endian)
    tag_byte_length = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian

    tag_data_offset = dmfile.tell()

    _read_tag_garbage_str(dmfile)

    (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

    dmfile.seek(tag_data_offset + tag_byte_length)
    return DM4TagHeader(tag_type, tag_name, tag_byte_length, tag_array_length, tag_array_types[0], tag_header_offset,
                        tag_data_offset)


class DMReader(sidpy.Reader):
    debugLevel = -1

    """
    file_path: filepath to dm3 file.

    warn('This Reader will eventually be moved to the ScopeReaders package'
         '. Be prepared to change your import statements',
         FutureWarning)
    """

    def __init__(self, file_path, verbose=True):
        super().__init__(file_path)

        # initialize variables ##
        self.verbose = verbose
        self.__filename = file_path
        self.__chosen_image = -1

        # - open file for reading
        try:
            self.__dm_file = open(self.__filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        # - create Tags repositories

        self.dm_version, self.file_size, self.endian, self.DM_header_size = read_header_dm(self.__dm_file)

        if self.verbose:
            print("Header info.:")
            print("- file version:", self.dm_version)
            print("- le:", self.endian)
            print("- file size:", self.file_size, "bytes")

        # don't read but close file
        self.close()

    def close(self):
        self.__dm_file.close()

    def read(self):
        try:
            self.__dm_file = open(self.__filename, 'rb')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')

        t1 = time.time()
        self.__dm_file.seek(self.DM_header_size)

        self.__stored_tags = {'DM': {'file_version': self.dm_version, 'file_size': self.file_size}}

        self.__read_tag_group(self.__stored_tags)

        if self.verbose:
            print("-- %s Tags read --" % len(self.__stored_tags))

        if self.verbose:
            t2 = time.time()
            print(f"| parse DM{self.dm_version} file: {(t2 - t1):.3g} s")


    def __read_tag_group(self, tags):
        issorted, isclosed, num_tags = read_tag_dir_header_dm(self.__dm_file,self.endian,self.dm_version)

        # read Tags
        print (type, 'num_tags', num_tags)
        for i in range(num_tags):
            tag_type = struct.unpack_from(self.endian + 'B', self.__dm_file.read(1))[0]

            is_data = (tag_type == 21)

            tag_label = _read_tag_name(self.__dm_file, self.endian)

            if is_data:
                value = _read_tag_data(self.__dm_file, self.endian)
                tags[tag_label] = value
            else:
                tags[tag_label] = {}
                self.__read_tag_group(tags[tag_label])
        return 1


data_path = os.path.join(os.path.dirname(__file__), '../../../../../data')
print(data_path)
file_path = os.path.join (data_path, 'EELS_STO.dm3')
reader = DMReader(file_path)
f = reader.read()
