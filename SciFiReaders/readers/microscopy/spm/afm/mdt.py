

import numpy as np
import sidpy
from sidpy.sid import Reader
import io
from struct import *

#decarator has been copied from the https://github.com/symartin/PyMDT
class MDTBufferedReaderDecorator(object):
    """
        a decorator class that facilitate the sequential reading of a file.

        The class will redirect al the standard file methods and add some methods to read and integer and float number
        encoded on 8, 16, 32 or 64 bits
    """

    def __init__(self, file_):
        self._file = file_

    def shift_position(self, shift_bytes):
        self._file.seek(shift_bytes, io.SEEK_CUR)

    def read_uint8(self):
        """Read a unsigned integer coded on 1 byte (a char)"""
        return unpack("<B", self._file.read(1))[0]

    def read_uint16(self):
        """Read a unsigned integer coded on 2 byte (a short)"""
        return unpack("<H", self._file.read(2))[0]

    def read_uint32(self):
        """Read a unsigned integer coded on 4 byte (a usual int or long int)"""
        return unpack("<I", self._file.read(4))[0]

    def read_uint64(self):
        """Read a unsigned integer coded on 8 byte (a long long)"""
        return unpack("<Q", self._file.read(8))[0]

    def read_int8(self):
        """Read a signed integer coded on 1 byte (a char)"""
        return unpack("<b", self._file.read(1))[0]

    def read_int16(self):
        """Read a signed integer coded on 2 byte (a short)"""
        return unpack("<h", self._file.read(2))[0]

    def read_int32(self):
        """Read a unsigned integer coded on 4 byte (a usual int or long int)"""
        return unpack("<i", self._file.read(4))[0]

    def read_int64(self):
        """Read a unsigned integer coded on 8 byte (a long long)"""
        return unpack("<q", self._file.read(8))[0]

    def read_char(self):
        """Read one character coded on 1 byte (a usual char)"""
        return unpack("<c", self._file.read(1))[0]

    def read_uchar(self):
        """Read a unsigned integer coded on 1 byte (a char)
            idem that read_uint8()
        """
        return int(unpack('<B', self._file.read(1))[0])

    def read_double(self):
        return float(unpack('<d', self._file.read(8))[0])

    def read_float32(self):
        """Read a signed float coded on 4 byte (a float)"""
        return float(unpack('<f', self._file.read(4))[0])

    def read_float64(self):
        """Read a signed float coded on 8 byte (au double float)"""
        return float(unpack('<d', self._file.read(8))[0])

    def __getattr__(self, attr):
        return getattr(self._file, attr)

class MDTReader(Reader):
    """
        Extracts data and metadata from NT-MDT (.mdt) binary files containing
        images or curves.

    """

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)

    def read(self, verbose=False):
        self._file = MDTBufferedReaderDecorator(open(self._input_file_path, mode='rb'))
        #read header of the file
        self._read_header()

        if verbose:
            print(f'File size: {self._file_size}')
            print(f'Number of frames: {self.nb_frame}')
            print()

        #iterator for the frames inside the file
        for i in range(self.nb_frame):
            self._frame = Frame(decorator = self._file)

            # 2d scan
            if self._frame.type == 106:
                self._frame._read_mda_frame()

            if verbose:
                print(f'Frame #{i}: type - {self._frame.type}, '
                      f'size - {self._frame.size}, '
                      f'start_position - {self._frame.start_pos},')
                print(f'version - {self._frame.version}, '
                      f'time - {self._frame.date}, '
                      f'var_size - {self._frame.var_size}, '
                      f'uuid - {self._frame.uuid}')
                print(f'title - {self._frame.title}, '
                      f'dimensions - {self._frame.n_dimensions}, '
                      f'measurands - {self._frame.n_measurands}, '
                      )



            #self._file.shift_position(self._frame.size - 8 - 12 - 2 - 24)




        self._file.close()

    def _read_header(self):
        '''

        Read of the header of MDT file contained information about a number of frames (self.nb_frame)
        and file size (self._file_size)

        '''
        # magic header
        self._file.shift_position(4)

        # File frm_byte_size (w/o header)
        self._file_size = self._file.read_uint32()

        #  4 bytes reserved (??)
        self._file.shift_position(4)

        # last frame
        self.nb_frame = self._file.read_uint16() + 1 #it originally returns number of frame -1, due to numeration from zero

        #  19 bytes reserved (??)
        self._file.shift_position(19)



    def can_read(self):
        """
        Tests whether or not the provided file has a .ibw extension
        Returns
        -------

        """
        return super(MDTReader, self).can_read(extension='mdt')


class Frame:
    '''
    Class for 2D frames
    '''
    def __init__(self, decorator=None):
        self._file = decorator
        self._read_frame_header()
        #TODO how to extract one frame without iteration?

    def _read_frame_header(self):

        '''Extract data common for all type of frames'''

        self.start_pos = self._file.tell()
        self.size = self._file.read_uint32()
        self.type = self._file.read_uint16()
        # frame version
        _version_minor = self._file.read_uint8()
        _version_major = self._file.read_uint8()
        self.version = _version_major + _version_minor*1e-1
        # date and time
        _year = self._file.read_uint16()
        _month = self._file.read_uint16()
        _day = self._file.read_uint16()
        _hour = self._file.read_uint16()
        _min = self._file.read_uint16()
        _sec = self._file.read_uint16()
        self.date = f'{_month}/{_day}/{_year} {_hour}:{_min}:{_sec}'

        self.var_size = self._file.read_uint16()

    def _read_mda_frame(self):
        '''read mda frame'''

        #skip frame header
        self._file.seek(self.start_pos+22)

        _head_size = self._file.read_uint32()
        _total_length = self._file.read_uint32()
        #uuid of frame
        self.uuid = ''
        for _ in range(16):
            self.uuid = self.uuid + str(self._file.read_uint8())

        #uuid is written 2 times
        self._file.shift_position(16)

        # skip 4 empty bytes
        self._file.shift_position(4)

        #size of name and xml
        _name_size  = self._file.read_uint32()
        _xml_size   = self._file.read_uint32()
        #some metrics
        _info_size  = self._file.read_uint32()
        _spec_size  = self._file.read_uint32()
        _source_info_size = self._file.read_uint32()
        _var_size = self._file.read_uint32()
        _data_offset = self._file.read_uint32()
        _data_size = self._file.read_uint32()

        #extract metadata and title
        if _name_size !=0:
            self.title = self._file.read(_name_size).decode('utf-8')
        if _xml_size != 0:
            self.xml_metadata = self._file.read(_xml_size).decode('utf-16')

        #don't understand self.info, self.spec, self.source_info
        if _info_size != 0:
            self.info = self._file.read(_info_size)
        if _spec_size != 0:
            self.spec = self._file.read(_spec_size)
        if _source_info_size != 0:
            self.source_info = self._file.read(_source_info_size)

        #skip _var_size
        self._file.shift_position(4)


        _struct_len = self._file.read_uint32()
        _array_size = self._file.read_uint64()
        _cell_size = self._file.read_uint32()

        self.n_dimensions = self._file.read_uint32()
        self.n_measurands = self._file.read_uint32()

        self._file.seek(self.start_pos + self.size)









