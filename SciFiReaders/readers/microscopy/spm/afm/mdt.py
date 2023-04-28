import numpy as np
import sidpy as sid
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

    def read_float32(self):
        """Read a signed float coded on 4 byte (a float)"""
        return float(unpack('<f', self._file.read(4))[0])

    def read_float64(self):
        """Read a signed float coded on 8 byte (au double float)"""
        return float(unpack('<d', self._file.read(8))[0])

    def extract_string(self, string_len):
        string_bytes = self._file.read(string_len)
        # in don't really know why but decode('utf-8) does't work for '°'
        return "".join(map(chr, string_bytes))

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
        '''
        Reads the file given in file_path into a list of sidpy dataset

        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Multi-channel inputs are separated into individual dataset objects
        '''
        self._file = MDTBufferedReaderDecorator(open(self._input_file_path, mode='rb'))

        #read header of the file
        self._read_header()

        if verbose:
            print(f'File size: {self._file_size}')
            print(f'Number of frames: {self.nb_frame}')
            print()
        dataset_list = []
        #iterator for the frames inside the file
        for i in range(self.nb_frame):
            self._frame = Frame(decorator = self._file)

            # 2d scan
            if self._frame.type == 106:
                self._frame._read_mda_frame()

            dataset_list.append(self._frame.data)

            if verbose:
                print(f'Frame #{i}: type - {self._frame.type}, '
                      f'size - {self._frame.size}, '
                      f'start_position - {self._frame.start_pos},')
                print(f'version - {self._frame.version}, '
                      f'time - {self._frame.date}, '
                      f'var_size - {self._frame.var_size}, '
                      f'uuid - {self._frame.uuid}\n'
                      f'title - {self._frame.title}, '
                      f'n_dimensions - {self._frame.n_dimensions}, '
                      f'n_measurands - {self._frame.n_measurands},\n'
                      f'dimensions - {self._frame.dimensions[0]},\n'
                      f'measurands - {self._frame.measurands[0]}'
                      f'\n\n')

        self._file.close()

        return dataset_list

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
    Class for MDA frames
    '''
    def __init__(self, decorator=None):
        self._file = decorator
        self.MDT_data_types = {-1: self._file.read_int8,
                               1: self._file.read_uint8,
                               -2: self._file.read_int16,
                               2: self._file.read_uint16,
                               -4: self._file.read_int32,
                               4: self._file.read_uint32,
                               -8: self._file.read_int64,
                               8: self._file.read_uint64,
                               -5892: self._file.read_float32,
                               -13320: self._file.read_float64}
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
        _current_pos = self._file.tell()
        _array_size = self._file.read_uint64()
        _cell_size = self._file.read_uint32()

        self.n_dimensions = self._file.read_uint32()
        self.n_measurands = self._file.read_uint32()

        self._file.seek(_struct_len + _current_pos)

        if self.n_dimensions > 0:
            self.dimensions = []
            for _ in range(self.n_dimensions):
                self.dimensions.append(self._read_mda_calibrations())

        if self.n_measurands > 0:
            self.measurands = []
            for _ in range(self.n_measurands):
                self.measurands.append(self._read_mda_calibrations())

        if self.n_dimensions == 2 and self.n_measurands == 1:
            self.data = self._extract_2d_frame()

        self._file.seek(self.start_pos + self.size)

    def _read_mda_calibrations(self):
        '''
        Read parameters and calibrations for mda frame

        Returns
        -------
        dict : dict with parameters
        '''
        _current_pos = self._file.tell()
        calibrations = {}

        #parameters length for further parsings
        _len_tot     = self._file.read_uint32()
        _len_struct  = self._file.read_uint32()

        _pos_after_struct = self._file.tell() + _len_struct

        _len_name    = self._file.read_uint32()
        _len_comment = self._file.read_uint32()
        _len_unit    = self._file.read_uint32()

        calibrations['si_unit'] = self._file.read_uint64()
        calibrations['accuracy'] = self._file.read_float64()
        self._file.shift_position(8)
        calibrations['bias'] = self._file.read_float64()
        calibrations['scale'] = self._file.read_float64()
        calibrations['min_index'] = self._file.read_uint64()
        calibrations['max_index'] = self._file.read_uint64()
        calibrations['data_type'] = self._file.read_int32() #signed integer
        calibrations['length'] = calibrations['max_index'] - calibrations['min_index'] + 1


        _len_author = self._file.read_uint32()

        #?
        self._file.seek(_pos_after_struct)

        if _len_name > 0:
            calibrations['name'] = self._file.extract_string(_len_name)
        if _len_comment > 0:
            calibrations['comment'] = self._file.extract_string(_len_comment)
        if _len_unit > 0:
            calibrations['unit'] = self._file.extract_string(_len_unit)
        if _len_author > 0:
            calibrations['author'] = self._file.extract_string(_len_author)

        self._file.seek(_current_pos + _len_tot)
        return calibrations

    def _extract_2d_frame(self):
        '''
        Extract data from 2d scan

        Returns
        -------
        sidpy.Dataset : 2d dataset object with AFM image data
        '''
        x = self.dimensions[1]
        y = self.dimensions[0]
        z = self.measurands[0]

        total_len = x['length'] * y['length']

        xreal = x['scale'] * (x['length'] - 1)
        yreal = y['scale'] * (y['length'] - 1)


        read_data = self.MDT_data_types[z['data_type']]

        data = np.zeros(total_len)

        #read data
        for i in range(len(data)):
            data[i] = z['bias'] + z['scale'] * read_data()

        data = np.reshape(data, (x['length'],y['length']))

        # Convert it to sidpy dataset object
        data_set = sid.Dataset.from_array(data)
        data_set.title = self.title
        data_set.data_type = 'Image'

        # Add quantity and units
        data_set.units = z['unit']
        data_set.quantity = self.title.split(':')[-1]

        # Add dimension info
        data_set.set_dimension(0, sid.Dimension(np.linspace(0, xreal, x['length']),
                                                name='x',
                                                units=x['unit'], quantity='x',
                                                dimension_type='spatial'))
        data_set.set_dimension(1, sid.Dimension(np.linspace(0, yreal, y['length']),
                                                name='y',
                                                units=y['unit'], quantity='y',
                                                dimension_type='spatial'))
        return data_set



#










