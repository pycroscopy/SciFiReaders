"""
Author: Pranav Sudersan
Date: February 2025

This module provides classes and functions for reading and processing WSxM/Nanotec AFM controller files.
It includes SID readers for 1D, 2D, and 3D data formats as three separate classes:

Classes:
--------
WSxM2DReader(Reader)
    A reader class for extracting 2D WSxM data and metadata (e.g., topography, phase, adhesion, etc.)
    and converting them into a dictionary of SID Dataset objects for all channels and directions
    of the measurement.

WSxM1DReader(Reader)
    A reader class for extracting 1D WSxM data and metadata (e.g., force spectroscopy, tune, etc.)
    and converting them into a dictionary of SID Dataset objects for all channels and directions
    of the measurement.

WSxM3DReader(Reader)
    A reader class for extracting 3D WSxM data and metadata (e.g., force volume, video, etc.)
    and converting them into a dictionary of SID Dataset objects for all channels and directions
    of the measurement.

WSxMFuncs
    A class containing optional static methods to directly read WSxM files, including reading headers,
    image data, and spectroscopy curves without the SID format. These methods are used by the above
    WSxM reader classes but can also be used independently for reading WSxM files, and they offer
    additional input parameters.

Usage:
------
To use the readers, instantiate the appropriate reader class with the file path and call the
read method to extract the data and metadata.

Example:
--------
    data_file_path = '/path/to/wsxm/file'
    reader = WSxM2DReader(data_file_path)
    data = reader.read()
    for channel, dataset in data.items():
        print(channel, dataset.quantity, dataset.direction)
        dataset.plot()
"""

import struct
import re
import sys
import numpy as np
import sidpy as sid
from sidpy.sid import Reader
from pathlib import Path
from matplotlib import pyplot as plt


# Read two dimensional AFM image data (e.g. Topography, Phase etc.)
class WSxM2DReader(Reader):
    def __init__(self, file_path, *args, **kwargs):
        """
        A reader class for extracting 2 dimensional WSxM data and metadata (e.g. topography, 
        phase, adhesion etc) and converting them into a dictionary of SID Dataset objects 
        for all channels and directions of the measurement.

        Parameters
        ----------
        file_path : str
            Path to the input file to be read.
        *args : tuple, optional
            Additional arguments to pass to the parent sidpy Reader class.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the parent sidpy Reader class.

        Methods
        -------
        read()
            Extracts the data and metadata from the input 2D data file and returns it as
            a dictionary of sidpy.Dataset objects.
        """
        super().__init__(file_path, *args, **kwargs)


    def read(self):
        """
        Reads and processes 2D WSxM files.
        Returns:
            dict: A dictionary where keys are channel identifiers ("Channel_xxx") and values are 
                    sidpy.Dataset objects containing the extracted data and metadata.
        """

        filepath = Path(self._input_file_path)
        filepath_all = WSxMFuncs._wsxm_get_common_files(filepath) #get all files of measurement, with common base name
        datasets = {}
        channel_number = 0 #channel number
        for path_i in filepath_all:
            path_ext = path_i.suffix  #file extension
            if path_ext != '.gsi': #ignore *.gsi files sharing same name               
                file = open(f'{path_i}','rb')
                header_dict, pos = WSxMFuncs._wsxm_readheader(file)
                header_dict['File path'] = path_i #file path included to header
                chan_label = header_dict['Acquisition channel [General Info]']
                data_dict_chan, pos = WSxMFuncs._wsxm_readimg(file, header_dict, pos)
                file.close()
                if 'X scanning direction [General Info]' in header_dict.keys():
                    x_dir = header_dict['X scanning direction [General Info]']
                else:
                    x_dir = None

                data_set = sid.Dataset.from_array(np.flip(data_dict_chan['data']['Z'].T),
                                                  title=chan_label)
                
                #Add quantity and units
                data_set.units = data_dict_chan['units']['Z']
                data_set.quantity = chan_label
                data_set.direction = x_dir #image direction information
                data_set.data_type = 'image'                

                #Add dimension info
                data_set.set_dimension(0, sid.Dimension(data_dict_chan['data']['X'],
                                                        name = 'x',
                                                        units=data_dict_chan['units']['X'], 
                                                        quantity = 'x',
                                                        dimension_type='spatial'))
                data_set.set_dimension(1, sid.Dimension(data_dict_chan['data']['Y'],
                                                        name = 'y',
                                                        units=data_dict_chan['units']['Y'], 
                                                        quantity='y',
                                                        dimension_type='spatial')) 
                #Writing the metadata
                data_set.metadata = data_dict_chan['header'].copy()

                #Add dataset to dictionary
                key_channel = f"Channel_{int(channel_number):03d}"
                datasets[key_channel] = data_set
                channel_number += 1

        return datasets

# Read one dimensional AFM data (e.g. force-distance curves)        
class WSxM1DReader(Reader):
    def __init__(self, file_path, *args, **kwargs):
        """
        A reader class for extracting 1 dimensional WSxM data and metadata (e.g. force 
        spectroscopy, tune etc) and converting them into a dictionary of SID Dataset objects 
        for all channels and directions of the measurement.

        Parameters
        ----------
        file_path : str
            Path to the input file to be read.
        *args : tuple, optional
            Additional arguments to pass to the parent sidpy Reader class.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the parent sidpy Reader class.

        Methods
        -------
        read()
            Extracts the data and metadata from the input 1D data file and returns it as
            a dictionary of sidpy.Dataset objects.
        """    
        super().__init__(file_path, *args, **kwargs)

    def read(self):
        """
        Reads and processes 1D WSxM files.
        Returns:
            dict: A dictionary where keys are channel identifiers ("Channel_xxx") and values are 
                    sidpy.Dataset objects containing the extracted data and metadata.
        """
        filepath = Path(self._input_file_path)
        filepath_all = WSxMFuncs._wsxm_get_common_files(filepath) #get all files of measurement, with common base name

        data_dict_chan = {}
        data_dict_stp = {} #dictionary for *.stp files to combine approach and retract data from separate files
        datasets = {}
        channel_number = 0 #channel number
        for path_i in filepath_all:
            path_ext = path_i.suffix                
            if path_ext == '.curves': # read *.curves spectroscopy files
                temp_dict, chan_label = WSxMFuncs._wsxm_readcurves(path_i)
                if chan_label not in data_dict_chan.keys():
                    data_dict_chan[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys(): #replace with *.curves data even if it already exists (more robust)
                        data_dict_chan[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.stp': # read *.stp spectroscopy files
                temp_dict, chan_label = WSxMFuncs._wsxm_readstp(path_i, data_dict_stp)
                if chan_label not in data_dict_chan.keys(): #ignore data if *.curves already found
                    data_dict_chan[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict_chan[chan_label]['curves'].keys():
                            data_dict_chan[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.cur': # read *.cur spectroscopy files
                temp_dict, chan_label = WSxMFuncs._wsxm_readcur(path_i)
                if chan_label not in data_dict_chan.keys(): #ignore data if *.curves already found
                    data_dict_chan[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict_chan[chan_label]['curves'].keys():
                            data_dict_chan[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()        

        #convert data dictionary to SID dataset
        for chan_i, chandata_i in data_dict_chan.items():
            for curv_i, curvdata_i in chandata_i['curves'].items():
                curve_list = []
                curve_dir_list = []
                for curv_dir_i, curvdata_dir_i in curvdata_i['data'].items():
                    curve_list.append(curvdata_dir_i['y'])
                    curve_dir_list.append(curv_dir_i)
                    x_data_i = curvdata_dir_i['x']
                curve_matrix = np.vstack(curve_list).T

                data_set = sid.Dataset.from_array(curve_matrix, title=f'{chan_i} ({curv_i})')
                
                #Add quantity and units
                data_set.units = curvdata_i['units']['y']
                data_set.quantity = chan_i
                data_set.direction = curve_dir_list #image direction information
                data_set.data_type = 'spectrum'                

                #Add dimension info
                data_set.set_dimension(0, sid.Dimension(x_data_i,
                                                        name = 'x',
                                                        units=curvdata_i['units']['x'],
                                                        quantity = 'x',
                                                        dimension_type='spatial'))
                
                #Writing the metadata
                data_set.metadata = curvdata_i['header'].copy()

                #Add dataset to dictionary
                key_channel = f"Channel_{int(channel_number):03d}"
                datasets[key_channel] = data_set
                channel_number += 1

        return datasets


# Read three dimensional AFM image data (e.g. Force volume, video etc)
class WSxM3DReader(Reader):
    def __init__(self, file_path, *args, **kwargs):
        """
        A reader class for extracting 3 dimensional WSxM data and metadata (e.g. Force 
        volume, video etc) and converting them into a dictionary of SID Dataset objects 
        for all channels and directions of the measurement.

        Parameters
        ----------
        file_path : str
            Path to the input file to be read.
        *args : tuple, optional
            Additional arguments to pass to the parent sidpy Reader class.
        **kwargs : dict, optional
            Additional keyword arguments to pass to the parent sidpy Reader class.

        Methods
        -------
        read()
            Extracts the data and metadata from the input 3D data file and returns it as
            a dictionary of sidpy.Dataset objects.
        """
        super().__init__(file_path, *args, **kwargs)


    def read(self):
        """
        Reads and processes 3D WSxM files.
        Returns:
            dict: A dictionary where keys are channel identifiers ("Channel_xxx") and values are 
                    sidpy.Dataset objects containing the extracted data and metadata.
        """

        filepath = Path(self._input_file_path)
        filepath_all = WSxMFuncs._wsxm_get_common_files(filepath) #get all files of measurement, with common base name

        datasets = {}
        channel_number = 0 #channel number
        for path_i in filepath_all:
            path_ext = path_i.suffix
            if path_ext == '.gsi': #force volume data from *.gsi files
                data_dict_chan, chan_label, topo_data = WSxMFuncs._wsxm_readforcevol(path_i)
                zz_data_type = sid.DataType.SPECTRAL_IMAGE 
                z_dimension_type = 'spectral'
            elif path_ext in ['.MOV', '.mpp']: #movie data files
                data_dict_chan, chan_label = WSxMFuncs._wsxm_readmovie(path_i)
                zz_data_type = sid.DataType.IMAGE_STACK  
                z_dimension_type = 'frame'
            else:
                assert("Invalid file type. Please choose *.gsi/*.MOV/*.mpp file")

            #image rotated to correct orientation of measurement in final dataset
            data_set = sid.Dataset.from_array(np.flip(np.rot90(data_dict_chan['data']['ZZ'], k=1, axes=(2,1)), axis=1),
                                                title=chan_label)
            
            #Add quantity and units
            data_set.units = data_dict_chan['units']['ZZ']
            data_set.quantity = chan_label
            data_set.data_type = zz_data_type            

            #Add dimension info
            data_set.set_dimension(0, sid.Dimension(data_dict_chan['data']['Z'],
                                                    name = 'z',
                                                    units=data_dict_chan['units']['Z'], 
                                                    quantity = 'z',
                                                    dimension_type=z_dimension_type))
            data_set.set_dimension(1, sid.Dimension(data_dict_chan['data']['X'],
                                                    name = 'x',
                                                    units=data_dict_chan['units']['X'], 
                                                    quantity='x',
                                                    dimension_type='spatial'))
            data_set.set_dimension(2, sid.Dimension(data_dict_chan['data']['Y'],
                                                    name = 'y',
                                                    units=data_dict_chan['units']['Y'], 
                                                    quantity='y',
                                                    dimension_type='spatial')) 
            
            #Writing the metadata            
            header_spectroscopy = {k: v for k, v in data_dict_chan['header'].items() if "[Spectroscopy images ramp value list]" in k or "[maxmins list]" in k}
            header_general = {k: v for k, v in data_dict_chan['header'].items() if k not in header_spectroscopy.keys()}
            data_set.metadata = header_general.copy()
            data_set.metadata['Spectroscopy metadata'] = header_spectroscopy
            if zz_data_type == sid.DataType.SPECTRAL_IMAGE: 
                data_set.direction = data_dict_chan['header']['Spectroscopy type [General Info]'] #image direction information
                #create topography dataset
                data_set_topo = sid.Dataset.from_array(np.flip(topo_data.T), title='Topography')
                data_set_topo.set_dimension(0, sid.Dimension(data_dict_chan['data']['X'],
                                                    name = 'x',
                                                    units=data_dict_chan['units']['X'], 
                                                    quantity='x',
                                                    dimension_type='spatial'))
                data_set_topo.set_dimension(1, sid.Dimension(data_dict_chan['data']['Y'],
                                                        name = 'y',
                                                        units=data_dict_chan['units']['Y'], 
                                                        quantity='y',
                                                        dimension_type='spatial'))
                data_set_topo.units = data_dict_chan['units']['Z']
                data_set_topo.quantity = 'Topography'
                data_set_topo.direction = data_dict_chan['header']['Spectroscopy type [General Info]'].split(' ')[1] #image direction information
                data_set_topo.data_type = 'image'

                data_set.metadata['Topography'] = data_set_topo #topography data added to metadata
                
            elif zz_data_type == sid.DataType.IMAGE_STACK:
                data_set.direction = 'None'


            #Add dataset to dictionary
            key_channel = f"Channel_{int(channel_number):03d}"
            datasets[key_channel] = data_set
            channel_number += 1

        return datasets

# collection of general functions used in WSxM readers
class WSxMFuncs():
    """
    A class containing static methods for handling WSxM files, including reading headers,
    image data, and spectroscopy curves. These methods are used by the WSxM reader classes
    above but can also be used by itself for reading WSxM files, offering additional input 
    parameters.
    Methods
    -------
    _wsxm_get_common_files(filepath, ext=None)
    _wsxm_readheader(file, pos=0, inibyte=100)
    _wsxm_readimg(file, header_dict, pos)
    _wsxm_readcurves(filepath)
    """
    # binary data type definitions used in header file
    DATA_TYPES = {
        'short':(2,'h'),'short-data':(2,'h'), 'unsignedshort':(2,'H'),
        'integer-data':(4,'i'), 'signedinteger':(4,'i'),
        'float-data':(4,'f'), 'double':(8,'d')
                }
    
    #rename spectroscopy line to standard names: approach and retract
    SPECT_DICT = {
        'Forward': 'approach', 'Backward': 'retract',
        'b': 'retract', 'f': 'approach'
                } 

    
    @staticmethod
    def _wsxm_get_common_files(filepath, ext=None):
        """
        Retrieve a list of files corresponding to all the channels of the 
        chosen measurement file (including "Forward" and "Backward" data), if they exist.
        
        This function searches for files in the same directory as the provided
        `filepath` that share a common base name, identified by a 4-digit number
        in the filename (standard WSxM naming convention). The provided `filepath` 
        is always included as the first item in the returned list. Optionally, the 
        search can be filtered by file extension.
        
        Args:
            filepath (Path): The path to the reference file.
            ext (str, optional): The file extension to filter by (e.g. ".top", ".ch1", ".gsi" etc.). 
                     If None, all files with the common base name are included.
        
        Returns:
            list[Path]: A list of Path objects representing the files for all channels of the measurement, 
                with the provided `filepath` as the first item.
        
        Note:
            - If the data files were renamed later, this function may not work as expected. 
              It is recommended to avoid renaming the part of the file name before the 4-digit number.
        """

        path_dir = filepath.parent
        filename = filepath.name
        match = re.search(r'\_\d{4}', filename) #regex to find 4 digit number in filename
        if match == None: #return same file if no matches
            return [filepath]
        else:
            filename_com = filename[:match.start()+5]

        files = []
        for path_i in path_dir.iterdir():
            path_ext_i = path_i.suffix
            if ext != None and path_ext_i != ext: #if ext given, skip files dont match the extension
                continue
            if path_i.is_file() and path_i.name.startswith(filename_com):
                files.append(path_i) 
        files.remove(filepath) #make sure filepath is the first item in the list
        files.insert(0, filepath)
        return files


    #read WSxM header data
    @staticmethod
    def _wsxm_readheader(file, pos=0, inibyte=100):
        """
        Reads the header of a WSxM file and returns it as a dictionary.
        Parameters:
        file (file object): The file object to read from.
        pos (int, optional): The position in the file (in bytes) to start reading from. Defaults to 0.
        inibyte (int, optional): The initial number of bytes to read to find 'Image header size'. Defaults to 100.
        Returns:
            tuple: A tuple containing:
                - header_dict (dict): A dictionary containing the header information.
                - pos_new (int): The new position (in bytes) in the file after reading the header.
        """

        header_dict = {}
        title_list = []
        # Find header size
        file.seek(pos, 0)
        data = file.read(inibyte)
        for ln in data.splitlines():
            hd_lst = ln.decode('latin-1', errors='ignore').split(':')
            if len(hd_lst) == 2:
                if hd_lst[0] == 'Image header size':
                    header_size = int(hd_lst[1])
                    break
        # read header data
        file.seek(pos, 0)
        data = file.read(header_size)
        for ln in data.splitlines():
            hd_lst = ln.decode('latin-1', errors='ignore').split(':')
            if len(hd_lst) == 2:
                header_name = f"{hd_lst[0].strip()} {title_list[-1]}".strip()
                header_dict[header_name] = hd_lst[1].strip()
            elif len(hd_lst) == 1 and hd_lst[0] != '': #collect section tiles in header file
                title_list.append(hd_lst[0])
        
        pos_new = pos + header_size #bytes read so far
        return header_dict, pos_new

    #read WSxM binary image data
    @staticmethod
    def _wsxm_readimg(file, header_dict, pos):
        """
        Reads an image from a WSxM file and returns the image data along with updated position.
        Parameters:
        file (file object): The file object to read the image data from.
        header_dict (dict): Dictionary containing the header information of the WSxM file.
        pos (int): The current position in the file (in bytes) from where to start reading the image data.
        Returns:
            tuple: A tuple containing:
                - data_dict_chan (dict): A dictionary with the image data and header information.
                    - 'data' (dict): Contains the image data arrays.
                        - 'Z' (numpy.ndarray): The 2D image data (image data) calibrated and reshaped.
                        - 'X' (numpy.ndarray): The 1D X-axis data.
                        - 'Y' (numpy.ndarray): The 1D Y-axis data.
                    - 'header' (dict): A copy of the header dictionary.
                    - 'unit' (dict): Units for 'Z', 'X' and 'Y' data
                - pos (int): The updated position in the file after reading the image data.
        """

        data_format = header_dict['Image Data Type [General Info]']
        chan_label = header_dict['Acquisition channel [General Info]']
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        z_min = float(header_dict['Minimum [Miscellaneous]'])
        z_max = float(header_dict['Maximum [Miscellaneous]'])
        if 'X starting offset [General Info]' in header_dict.keys(): #for "3D mode" images
            x_offset = float(header_dict['X starting offset [General Info]'].split(' ')[0])
            y_offset = float(header_dict['Y starting offset [General Info]'].split(' ')[0])
        else:
            x_offset = 0
            y_offset = 0

        x_data = np.linspace(x_offset, x_len+x_offset, x_num, endpoint=True)
        y_data = np.linspace(y_len+y_offset, y_offset, y_num, endpoint=True)
        
        #read binary image data
        point_length, type_code  = WSxMFuncs.DATA_TYPES[data_format]
        file.seek(pos, 0)
        data_len = x_num*y_num*point_length
        bin_data = file.read(data_len)
        ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()

        if z_len == 0: #for zero data
            z_calib = 1
        else:
            z_calib = z_len/(z_max-z_min)
        
        z_unit = header_dict['Z Amplitude [General Info]'].split(' ')[-1]

        #the following fixes a bug in the data format for amplitude channel, ensures that data is read in volts, not nanometers (which is fake)
        if chan_label == 'Amplitude' and header_dict['Z Amplitude [General Info]'].split(' ')[1] != 'V':
            chan_factor = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            z_calib = z_calib/chan_factor
            z_unit = 'V'
        
        #img data dictionary
        data_dict_chan = {'data': {'Z': (z_calib*ch_array.reshape(x_num, y_num)),
                                'X': x_data,
                                'Y': y_data},
                        'header': header_dict.copy(),
                        'units': {'Z': z_unit,
                                  'X': header_dict['X Amplitude [Control]'].split(' ')[-1],
                                  'Y': header_dict['Y Amplitude [Control]'].split(' ')[-1]
                                  }
                        }
        
        pos += data_len #bytes read so far
        
        return data_dict_chan, pos

    # read *.curves file with image and f-d curves
    @staticmethod
    def _wsxm_readcurves(filepath):
        """
        Reads WSxM spectroscopy curves (*.curves format) from a given file.
        Args:
            filepath (str): The path to the WSxM file to be read.
        Returns:
            tuple: A tuple containing:
            - data_dict (dict): A dictionary containing the parsed data from the file.
            - y_label (str): The channel name of the Y-axis data.
        The structure of the returned data_dict is as follows:
        {
            'Y axis channel label': {
            'image': {
                'data': {
                'Z': 2D array of embedded topography data,
                'X': 1D array of X-axis data,
                'Y': 1D array of Y-axis data
                },
                'header': header_dict
            },
            'curves': {
                curve_index: {
                'header': header_dict,
                'units': {'x': x_unit, 'y': y_unit},
                'data': {
                    'approach': {'x': x_data, 'y': y_data},
                    'retract': {'x': x_data, 'y': y_data}
                }
                }
            }
            }
        }
        """

        data_dict = {}
        file = open(f'{filepath}','rb')
        header_dict_top, pos = WSxMFuncs._wsxm_readheader(file)
        data_dict_chan, pos = WSxMFuncs._wsxm_readimg(file, header_dict_top, pos) 
        
        data_format = header_dict_top['Image Data Type [General Info]']
        point_length, type_code  = WSxMFuncs.DATA_TYPES[data_format]
        data_dict_curv = {}
        
        while True:
            header_dict, pos = WSxMFuncs._wsxm_readheader(file, pos=pos)
            header_dict['File path'] = filepath #file path included to header 
            line_pts = int(header_dict['Number of points [General Info]'])
            line_num = int(header_dict['Number of lines [General Info]'])
            y_label = header_dict['Y axis text [General Info]'].split('[')[0].strip()
            x_label = header_dict['X axis text [General Info]'].split('[')[0].strip()
            curv_ind = int(header_dict['Index of this Curve [Control]'])
            curv_num = int(header_dict['Number of Curves in this serie [Control]'])
            chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                chan_fact = -chan_fact
            chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])

            header_dict['Spectroscopy channel'] = y_label #Insert channel name information into dictionary
            
            line_order = ['approach', 'retract']
            if header_dict['First Forward [Miscellaneous]'] == 'No': #CHECK THIS
                line_order = ['retract', 'approach']

            data_len = line_pts*line_num*2*point_length
            file.seek(pos, 0)
            
            if line_pts == 0: #skip if no data for curve exists (bug in file format)
                continue
            
            bin_data = file.read(data_len)
            ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
            x_data = np.split(ch_array[::2], line_num)
            y_data = np.split(ch_array[1::2], line_num)

            for j in range(int(line_num/len(line_order))):
                k = len(line_order) * j
                curv_ind_j = f'{curv_ind}{chr(ord("a")+j)}' if line_num > 2 else curv_ind
                data_dict_curv[curv_ind_j] = {'header': header_dict_top.copy() | header_dict.copy(), #merge header dictionaries
                                              'data': {},
                                              'units': {'x': header_dict['X axis unit [General Info]'],
                                                        'y': header_dict['Conversion Factor 00 [General Info]'].split(' ')[-1]
                                                        }
                                            } 
                for i, curv_dir in enumerate(line_order):
                    data_dict_curv[curv_ind_j]['data'][curv_dir] = {
                        'x': x_data[k+i],
                        'y': chan_offs+(y_data[k+i]*chan_fact)
                        }                                                  
            
            if curv_ind == curv_num:
                break
            else:
                pos += data_len #bytes read so far
                file.seek(pos, 0)

        data_dict[y_label] = {'image': data_dict_chan,
                            'curves': data_dict_curv
                            }
        file.close()
        
        return data_dict, y_label

    # read *.cur WSxM file
    @staticmethod
    def _wsxm_readcur(filepath):
        """
        Reads WSxM spectroscopy curve (*.cur) files and extracts the data.
        Args:
            filepath (str): The path to the .cur file to be read.
        Returns:
            tuple: A tuple containing:
                - data_dict (dict): A dictionary containing the extracted data.
                - y_label (str): The channel name for the Y-axis data.
        The structure of the returned data_dict is as follows:
        {
            'Y axis channel label': {
                'curves': {
                    curve_index: {
                        'header': header_dict,
                        'units': {'x': x_unit, 'y': y_unit},
                        'data': {
                            'approach': {'x': x_data, 'y': y_data},
                            'retract': {'x': x_data, 'y': y_data}
                },
                'image': {}
            }
        }
        Note:
            - The 'image' key is empty in this case as it does not exist in .cur files.
        """

        data_dict = {}
        file = open(f'{filepath}','rb')
        header_dict, pos = WSxMFuncs._wsxm_readheader(file)
        header_dict['File path'] = filepath #file path included to header

        if 'Index of this Curve [Control]' in header_dict.keys(): #for spectroscopy curves
            line_num = int(header_dict['Number of lines [General Info]'])
            y_label = header_dict['Y axis text [General Info]'].split('[')[0].strip()
            x_label = header_dict['X axis text [General Info]'].split('[')[0].strip()
            if header_dict['Index of this Curve [Control]'] == 'Average': #for average curves
                curv_ind = header_dict['Index of this Curve [Control]']
            else:
                curv_ind = int(header_dict['Index of this Curve [Control]'])
            curv_num = int(header_dict['Number of Curves in this serie [Control]'])
            chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            y_unit = header_dict['Conversion Factor 00 [General Info]'].split(' ')[-1]
            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                chan_fact = -chan_fact
            chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])
            
            line_order = ['approach', 'retract']
            if header_dict['First Forward [Miscellaneous]'] == 'No': #CHECK THIS
                line_order = ['retract', 'approach']
        else: #for other kinds of *.cur (e.g. tune data)
            line_pts = int(header_dict['Number of points [General Info]'])
            line_num = int(header_dict['Number of lines [General Info]'])
            y_label = header_dict['Y axis text [General Info]'].split('[')[0].strip()
            x_label = header_dict['X axis text [General Info]'].split('[')[0].strip()
            #set generic values for irrelevant parameters here
            curv_ind = 1
            curv_num = 1
            chan_fact = 1
            chan_offs = 0  
            y_unit = header_dict['Y axis unit [General Info]']                         
            line_order = [f'{y_label}_{ln_i+1}' for ln_i in range(line_num)]
        
        header_dict['Spectroscopy channel'] = y_label #Insert channel name information into dictionary
        file.seek(pos, 0)
        data = file.read()
        data_list = []
        for ln in data.splitlines():
            ln_array = ln.decode('latin-1', errors='ignore').strip().replace('#QNAN','').split(' ')
            data_list.append(list(map(float,ln_array)))
        data_mat = np.array(data_list) #data matrix   

        if y_label not in data_dict.keys():
            data_dict[y_label] = {'curves':{}, 'image':{}}

        for j in range(int(line_num/len(line_order))):
            k = 2*len(line_order) * j
            curv_ind_j = f'{curv_ind}{chr(ord("a")+j)}' if line_num > 2 else curv_ind
            data_dict[y_label]['curves'][curv_ind_j] = {'header': header_dict.copy(), 
                                                        'data': {},
                                                        'units': {'x': header_dict['X axis unit [General Info]'],
                                                                'y': y_unit
                                                                }
                                                        }
            for i, curv_dir in enumerate(line_order):
                data_dict[y_label]['curves'][curv_ind_j]['data'][curv_dir] = {
                    'x': data_mat[:,k+(2*i)],
                    'y': chan_offs+(data_mat[:,k+(2*i+1)]*chan_fact) #converted to units
                    }

        file.close()
        
        return data_dict, y_label

    #read *.stp spectroscopy curves. Pass "data_dict" to update data of both approach and retract into it correctly
    @staticmethod
    def _wsxm_readstp(filepath, data_dict={}):
        """
        Reads a WSxM .stp spectroscopy file and extracts the data into a dictionary.
        Args:
            filepath (str): The path to the .stp file to be read.
            data_dict (dict, optional): A dictionary to store the extracted data. 
            Use this to combine "approach" and "retract" curve data spread across different files into the same dictionary passed here.
            Defaults to an empty dictionary.
        Returns:
            tuple: A tuple containing:
                - data_dict (dict): The dictionary containing the extracted data.
                - chan_label (str): The label of the spectroscopy channel.
        The structure of the returned data_dict is as follows:
        {
            'Channel label': {
                'curves': {
                    curve_index: {
                        'header': header_dict,
                        'units': {'x': x_unit', 'y': y_unit},
                        'data': {
                            'approach': {'x': x_data, 'y': y_data},
                            'retract': {'x': x_data, 'y': y_data}
                        }
                    }
                },
                'image': {}
            }
        }
        """

        file = open(f'{filepath}','rb')
        filename = filepath.name
        header_dict, pos = WSxMFuncs._wsxm_readheader(file)
        header_dict['File path'] = [filepath] #file path included to header
        data_format = header_dict['Image Data Type [General Info]']
        
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        x_dir = header_dict['X scanning direction [General Info]']
        y_dir = header_dict['Y scanning direction [General Info]']
        file_dirkey = filename.split('.')[-2]
        if len(file_dirkey) == 1:
            chan_label = filename.split('_')[-1].split('.')[0] 
            z_dir = WSxMFuncs.SPECT_DICT[filename.split('.')[-2]]
        else:
            file_dirkey_match = re.search(r'line\_\d{1}', file_dirkey)
            chan_label = file_dirkey[:file_dirkey_match.start()].split('_')[-1]
            z_dir = WSxMFuncs.SPECT_DICT[x_dir] 
            
        if 'X starting offset [General Info]' in header_dict.keys(): #for "3D mode" images
            x_offset = float(header_dict['X starting offset [General Info]'].split(' ')[0])
            y_offset = float(header_dict['Y starting offset [General Info]'].split(' ')[0])
        else:
            x_offset = 0
            y_offset = 0

        header_dict['Spectroscopy channel'] = chan_label #Insert channel name information into dictionary

        z_data = np.linspace(x_offset, x_offset+x_len, y_num, endpoint=True) #CHECK THIS
        #read binary image data
        point_length, type_code  = WSxMFuncs.DATA_TYPES[data_format]
        file.seek(pos, 0)
        data_len = x_num*y_num*point_length
        bin_data = file.read(data_len)
        ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten() 
        ch_mat = ch_array.reshape(x_num,y_num)
        if z_len == 0: #for zero data
            z_calib = 1
        else:
            z_calib = z_len/(ch_array.max()-ch_array.min())
        
        #create separate curve data for each line (consistent with '1D' data format)
        for i in range(x_num): 
            curv_ind = i + 1        
            #data dictionary initialised in a consistant format (also check wsxm_readcurves())
            if chan_label not in data_dict.keys():
                data_dict[chan_label] = {'curves': {}, 'image':{}}
            if curv_ind not in data_dict[chan_label]['curves'].keys():
                data_dict[chan_label]['curves'][curv_ind] = {'data': {},
                                                             'header': header_dict.copy(),
                                                             'units': {'x': header_dict['X Amplitude [Control]'].split(' ')[-1],
                                                                       'y': header_dict['Z Amplitude [General Info]'].split(' ')[-1]
                                                                       }
                                                            }
                #insert curve number info into header
                data_dict[chan_label]['curves'][curv_ind]['header']['Index of this Curve [Control]'] = str(curv_ind) 
                data_dict[chan_label]['curves'][curv_ind]['header']['Number of Curves in this serie [Control]'] = str(x_num)
            if z_dir not in data_dict[chan_label]['curves'][curv_ind]['data'].keys():
                data_dict[chan_label]['curves'][curv_ind]['data'][z_dir] = {}
            if filepath not in data_dict[chan_label]['curves'][curv_ind]['header']['File path']: #file path included to header
                data_dict[chan_label]['curves'][curv_ind]['header']['File path'].append(filepath)
            data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['x'] = z_data
            data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['y'] = (z_calib*ch_mat[:][i])
            if x_dir == 'Forward':
                data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['y'] = np.flip((z_calib*ch_mat[:][i]))

        file.close()
        
        return data_dict, chan_label
    

    def _wsxm_readforcevol(filepath):
        """
        Reads a WSxM .gsi force-volume data and extracts the data into a dictionary.
        Args:
            filepath (str): The path to the .stp file to be read.
        Returns:
            tuple: A tuple containing:
                - data_dict_chan (dict): The dictionary containing the extracted data.
                - chan_label (str): The label of the spectroscopy channel.
                - topo_data (numpy.ndarray): 2D array containing topography data.
        The structure of the returned data_dict_chan is as follows:
        {
            'header': header_dict,
            'units': {
                    'ZZ': data_unit,
                    'X': x_unit,
                    'Y': y_unit,
                    'Z': z_unit,
                    }
            'data': {
                    'ZZ': 3D data,
                    'X': x_data,
                    'Y': y_data,
                    'Z': z_data
                    },
            
        }
        """

        file = open(f'{filepath}','rb')
        header_dict, pos = WSxMFuncs._wsxm_readheader(file)
        header_dict['File path'] = filepath #file path included to header

        data_format = header_dict['Image Data Type [General Info]']
        chan_label = header_dict['Acquisition channel [General Info]']
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        chan_num = int(header_dict['Number of points per ramp [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        chan_adc2v = float(header_dict['ADC to V conversion factor [General Info]'].split(' ')[0])
        chan_fact = float(header_dict['Conversion factor 0 for input channel [General Info]'].split(' ')[0])
        chan_offs = float(header_dict['Conversion offset 0 for input channel [General Info]'].split(' ')[0]) #0

        chan_inv = header_dict['Channel is inverted [General Info]']
        if chan_inv == 'Yes':
            chan_fact = -chan_fact
                
        x_data = np.linspace(0, x_len, x_num, endpoint=True)
        y_data = np.linspace(y_len, 0, y_num, endpoint=True)
    
        z_data = np.empty(0)
        for i in range(chan_num):
            z_data = np.append(z_data, float(header_dict[f'Image {i:03} [Spectroscopy images ramp value list]'].split(' ')[0]))

        z_data = np.flip(z_data) #reverse z data order to make zero as point of contact
        
        #read binary image data
        point_length, type_code  = WSxMFuncs.DATA_TYPES[data_format]
        file.seek(pos, 0)
        data_len = x_num*y_num*point_length
        #read first topography data
        bin_data = file.read(data_len)
        topo_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
        if z_len == 0: #for zero data
            topo_calib = 1
        else:
            topo_calib = z_len/(topo_array.max()-topo_array.min())
        
        topo_data = topo_calib*topo_array.reshape(x_num, y_num) #topography data

        pos += data_len
        ch_array = np.empty(0) #initialize channel data array
        for i in range(1, chan_num+1):
            file.seek(pos, 0)
            bin_data = file.read(data_len)
            ch_array_temp = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
            ch_array = np.append(ch_array, chan_offs+(ch_array_temp*chan_adc2v*chan_fact))
            pos += data_len #next image
            
        #img data dictionary
        data_dict_chan = {'data': {'ZZ': ch_array.reshape(chan_num,y_num,x_num),#,
                                'X': x_data,
                                'Y': y_data,
                                'Z': z_data
                                },
                        'header': header_dict,
                        'units': {'ZZ': header_dict['Conversion factor 0 for input channel [General Info]'].split(' ')[-1],
                                    'X': header_dict['X Amplitude [Control]'].split(' ')[-1],
                                    'Y': header_dict['Y Amplitude [Control]'].split(' ')[-1],
                                    'Z': header_dict['Z Amplitude [General Info]'].split(' ')[-1],
                                    }
                        }
        
        file.close()
        
        return data_dict_chan, chan_label, topo_data

    def _wsxm_readmovie(filepath):
        """
        Reads a WSxM .MOV and .mpp movie data and extracts the data into a dictionary.
        Args:
            filepath (str): The path to the .stp file to be read.
        Returns:
            tuple: A tuple containing:
                - data_dict_chan (dict): The dictionary containing the extracted data.
                - chan_label (str): The label of the spectroscopy channel.
        The structure of the returned data_dict_chan is as follows:
        {
            'header': header_dict,
            'units': {
                    'ZZ': data_unit,
                    'X': x_unit,
                    'Y': y_unit,
                    'Z': z_unit,
                    }
            'data': {
                    'ZZ': 3D data,
                    'X': x_data,
                    'Y': y_data,
                    'Z': z_data
                    },
            
        }
        """

        file = open(f'{filepath}','rb')
        header_dict, pos = WSxMFuncs._wsxm_readheader(file)
        header_dict['File path'] = filepath #file path included to header

        data_format = header_dict['Image Data Type [General Info]']
        chan_label = header_dict['Acquisition channel [General Info]']
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        chan_num = int(header_dict['Number of Frames [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        z_min = float(header_dict['Minimum [Miscellaneous]'])
        z_max = float(header_dict['Maximum [Miscellaneous]'])
                
        x_data = np.linspace(0, x_len, x_num, endpoint=True)
        y_data = np.linspace(y_len, 0, y_num, endpoint=True)
        z_data = np.linspace(0, chan_num, chan_num, endpoint=True) #frame number array

        #read binary image data
        point_length, type_code  = WSxMFuncs.DATA_TYPES[data_format]
        data_len = x_num*y_num*point_length

        if z_len == 0: #for zero data
            z_calib = 1
        else:
            z_calib = z_len/(z_max-z_min)
        
        z_unit = header_dict['Z Amplitude [General Info]'].split(' ')[-1]
        #the following fixes a bug in the data format for amplitude channel, ensures that data is read in volts, not nanometers (which is fake)
        if chan_label == 'Amplitude' and header_dict['Z Amplitude [General Info]'].split(' ')[1] != 'V':
            chan_factor = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            z_calib = z_calib/chan_factor
            z_unit = 'V'

        ch_array = np.empty(0) #initialize channel data array
        for i in range(1, chan_num+1):
            file.seek(pos, 0)
            bin_data = file.read(data_len)
            ch_array_temp = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()          
            ch_array = np.append(ch_array, z_calib*ch_array_temp)
            pos += data_len #next image
            
        #img data dictionary
        data_dict_chan = {'data': {'ZZ': ch_array.reshape(chan_num,y_num,x_num),#,
                                'X': x_data,
                                'Y': y_data,
                                'Z': z_data
                                },
                        'header': header_dict,
                        'units': {'ZZ': z_unit,
                                    'X': header_dict['X Amplitude [Control]'].split(' ')[-1],
                                    'Y': header_dict['Y Amplitude [Control]'].split(' ')[-1],
                                    'Z': 'frame',
                                    }
                        }
        
        file.close()
        
        return data_dict_chan, chan_label
