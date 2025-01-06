import numpy as np
import sidpy as sid
from sidpy.sid import Reader
import struct
import os
import re
from pathlib import Path
from matplotlib import pyplot as plt

# binary data type definitions used in header file
DATA_TYPES = {
    'short':(2,'h'),'short-data':(2,'h'), 'unsignedshort':(2,'H'),
    'integer-data':(4,'i'), 'signedinteger':(4,'i'),
    'float-data':(4,'f'), 'double':(8,'d')
            }

#WSxM channel name definitions from its file extension
# WSXM_CHANNEL_DICT = {
#     'top':'Topography', 'ch1': 'Normal force', 'ch2': 'Lateral force',
#     'ch3': 'Sum', 'ch12': 'Excitation frequency', 'ch13': 'Amplitude (2nd Dynamic)',
#     'ch14':'Phase (2nd Dynamic)', 'ch15': 'Amplitude', 'ch16': 'Phase',
#     'adh': 'Adhesion', 'sti': 'Stiffness'
#                     }
# @staticmethod
def _wsxm_get_common_files(filepath, ext=None):
    # filepath = 'data/interdigThiols_tipSi3nN_b_0026.fb.ch1.gsi'
    path_dir = filepath.parent #os.path.dirname(filepath)
    filename = filepath.name #os.path.basename(filepath)
    # filename_com = os.path.basename(filepath).split('.')[0] #common file name
    match = re.search(r'\_\d{4}', filename) #regex to find 4 digit number in filename
    if match == None: #return same file for no matches #CHECK
        return [filepath] #print(filename)
    else:
        filename_com = filename[:match.start()+5]
    # print(filename_com)
    files = []
    # for i in os.listdir(path_dir):
    for path_i in path_dir.iterdir():
        # path_i = os.path.join(path_dir,i)
        path_ext_i = path_i.suffix #os.path.splitext(path_i)[1] #file extension
        if ext != None and path_ext_i != ext: #if ext given, skip files dont match the extension
            continue
        # if os.path.isfile(path_i) and i.startswith(filename_com):
        if path_i.is_file() and path_i.name.startswith(filename_com):
            files.append(path_i) 
    # print(files)
    files.remove(filepath) #make sure filepath is the first item in the list
    files.insert(0, filepath)
    return files


#read WSxM header data
# @staticmethod
def _wsxm_readheader(file, pos=0, inibyte=100):
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
                # print(header_size)
                break
    # read header data (NOTE THAT DUPLICATE HEADER NAMES (example P,I values) WILL BE SKIPPED!
    file.seek(pos, 0)
    data = file.read(header_size)#[:header_size]
    for ln in data.splitlines():
        hd_lst = ln.decode('latin-1', errors='ignore').split(':')
        if len(hd_lst) == 2:
            # header_name = hd_lst[0].strip()
            # if header_name in header_dict.keys():
            #     header_name = header_name + ' ' + header_dict['Header sections'][-1]
            header_name = f"{hd_lst[0].strip()} {title_list[-1]}".strip()
            header_dict[header_name] = hd_lst[1].strip()
        elif len(hd_lst) == 1 and hd_lst[0] != '': #collect section tiles in header file
            title_list.append(hd_lst[0])
    
    pos_new = pos + header_size #bytes read so far
    # print(header_dict)
    return header_dict, pos_new

# Read two dimensional AFM image data (e.g. Topography, Phase etc.)
class WSxM2DReader(Reader):
    """
    The above definition of the class states that our ExampleReader inherits all the capabilities and
    behaviors of the Reader class in sidpy and builds on top of it
    """
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)


    def read(self):
        """
        Extracts the data and metadata out of proprietary formatted files and writes it into a SID formatted HDF5 file


        Returns
        -------
        data_set: sidpy.Dataset object
            wraps all the raw data and metadata from the input file into a Dataset object
        """
        filepath = Path(self._input_file_path)
        # if all_files == True: #find all channels and directions of this measurement
        filepath_all = _wsxm_get_common_files(filepath)
        # else:
            # filepath_all = [filepath]
        # data_dict = {}
        datasets = {}
        channel_number = 0 #channel number
        for path_i in filepath_all:
            path_ext = path_i.suffix #os.path.splitext(path)[1] #file extension
            if path_ext != '.gsi': #ignore *.gsi files sharing same name
                # if all_files==True and mute == False:
                print(channel_number, path_i.name) #os.path.basename(path)) 
                
                file = open(f'{path_i}','rb')
                header_dict, pos = _wsxm_readheader(file)
                header_dict['File path'] = path_i #file path included to header
                chan_label = header_dict['Acquisition channel [General Info]']
                data_dict_chan, pos = self._wsxm_readimg(file, header_dict, pos)
                file.close()
                x_dir = header_dict['X scanning direction [General Info]']
                # if chan_label in data_dict.keys():
                #     data_dict[chan_label][x_dir] = data_dict_chan
                # else:
                #     data_dict[chan_label] = {}
                #     data_dict[chan_label][x_dir] = data_dict_chan
                data_set = sid.Dataset.from_array(data_dict_chan['data']['Z'],
                                                  title=chan_label)
                
                #Add quantity and units
                data_set.units = data_dict_chan['header']['Conversion Factor 00 [General Info]'].split(' ')[-1]
                data_set.quantity = chan_label
                data_set.direction = x_dir #image direction information
                data_set.data_type = 'image'                

                #Add dimension info
                data_set.set_dimension(0, sid.Dimension(data_dict_chan['data']['X'],
                                                        name = 'x',
                                                        units=data_dict_chan['header']['X Amplitude [Control]'].split(' ')[-1], 
                                                        quantity = 'x',
                                                        dimension_type='spatial'))
                data_set.set_dimension(1, sid.Dimension(data_dict_chan['data']['X'],
                                                        name = 'y',
                                                        units=data_dict_chan['header']['X Amplitude [Control]'].split(' ')[-1], 
                                                        quantity='y',
                                                        dimension_type='spatial')) 
                #Writing the metadata
                data_set.metadata = data_dict_chan['header'].copy()

                #Finally, append it
                #datasets.append(data_set)
                key_channel = f"Channel_{int(channel_number):03d}"
                datasets[key_channel] = data_set
                channel_number += 1
        # if all_files == True:
        #     # wsxm_calc_extrachans(data_dict, data_type='2D')
        #     return data_dict
        # else: #only return the specifc data dictionary for single file if all files are not read
        #     return data_dict_chan

        return datasets

    #read WSxM binary image data
    @staticmethod
    def _wsxm_readimg(file, header_dict, pos):
        data_format = header_dict['Image Data Type [General Info]']
        chan_label = header_dict['Acquisition channel [General Info]']
        line_rate = float(header_dict['X-Frequency [Control]'].split(' ')[0])
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        x_dir = header_dict['X scanning direction [General Info]']
        y_dir = header_dict['Y scanning direction [General Info]'] #CHECK Y DIRECTIONS
        #CHECK THIS FOR SECOND ARRAY! MAY NOT WORK FOR 3D Mode images!
        #THIS DOES NOT WORK. CHECK EVERYWHERE
        dsp_voltrange = float(header_dict['DSP voltage range [Miscellaneous]'].split(' ')[0])
        # chan_adc2v = 20/2**16
        # chan_fact = int(header_dict['Conversion Factor 00'].split(' ')[0])
        # chan_offs = 0#int(header_dict['Conversion Offset 00'].split(' ')[0])
        x_data = np.linspace(x_len, 0, x_num, endpoint=True) #if x_dir == 'Backward' else np.linspace(x_len, 0, x_num, endpoint=True)
        y_data = np.linspace(0, y_len, y_num, endpoint=True) #if y_dir == 'Down' else np.linspace(y_len, 0, y_num, endpoint=True)
        # xx_data, yy_data = np.meshgrid(x_data, y_data)
        
        #read binary image data
        point_length, type_code  = DATA_TYPES[data_format]
        # with open(filepath, 'rb') as file:
        file.seek(pos, 0)
        data_len = x_num*y_num*point_length
        bin_data = file.read(data_len)
        # print(data.read()[(x_num*y_num*point_length)+header_size:])
        ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
        #dac to volt conversion
        if chan_label == 'Topography': #ignore for topo
            chan_offs = 0
            if z_len == 0: #for zero data
                z_calib = 1
                # chan_fact = 1
                # chan_offs = 0
            else:
                z_calib = z_len/(ch_array.max()-ch_array.min())
                # chan_fact = 1
                # chan_offs = 0
        else: #other channel data stored in volts
            z_calib = dsp_voltrange/(2**16)
            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                z_calib = -z_calib
            chan_offs = 0
            # chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            if chan_label == 'Excitation frequency': #for freq shift
                z_calib = z_calib * float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
                chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0]) #CHECK THIS!
        # z_calib2 = z_len/(ch_array.max()-ch_array.min())
        # print(z_calib, z_calib2, z_calib-z_calib2)
        
        #img data dictionary
        data_dict_chan = {'data': {'Z': z_calib*ch_array.reshape(x_num, y_num) + chan_offs,
                                'X': x_data,
                                'Y': y_data},
                        'header': header_dict.copy()}
        
        pos += data_len #bytes read so far
        return data_dict_chan, pos

# Read one dimensional AFM data (e.g. force-distance curves)        
class WSxM1DReader(Reader):
    """
    The above definition of the class states that our ExampleReader inherits all the capabilities and
    behaviors of the Reader class in sidpy and builds on top of it
    """
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)

    def read(self):
        """
        Extracts the data and metadata out of proprietary formatted files and writes it into a SID formatted HDF5 file


        Returns
        -------
        data_set: sidpy.Dataset object
            wraps all the raw data and metadata from the input file into a Dataset object
        """
        filepath = Path(self._input_file_path)
        # if all_files == True: #find all channels and directions of this measurement
        filepath_all = _wsxm_get_common_files(filepath)
        # else:
            # filepath_all = [filepath]
        data_dict = {}
        datasets = {}
        channel_number = 0 #channel number
        for path_i in filepath_all:
            path_ext = path_i.suffix #os.path.splitext(path)[1] #file extension
            # if path_ext != '.gsi': #ignore *.gsi files sharing same name
                # if all_files==True and mute == False:
            print(channel_number, path_i.name) #os.path.basename(path)) 
                
            if path_ext == '.curves': # read *.curves spectroscopy files
                temp_dict, chan_label = wsxm_readcurves(path_i)
                if chan_label not in data_dict.keys():
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys(): #replace with *.curves data even if it already exists (more robust)
                        data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.stp': # read *.stp spectroscopy files
                temp_dict, chan_label = wsxm_readstp(path_i, data_dict_stp)
                if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                            data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.cur': # read *.cur spectroscopy files
                temp_dict, chan_label = wsxm_readcur(path_i)
                if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                            data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()

            for chan_i, chandata_i in data_dict.items():
                curve_list = []
                for curv_i, curvdata_i in chandata_i['curves'].items():
                    curve_list.append(curvdata_i['y'])
                curve_matrix = np.vstack(curve_list).T
                #CHECK THIS BLOCK!!!
                data_set = sid.Dataset.from_array(curve_matrix, title=chan_i)
                
                #Add quantity and units
                data_set.units = data_dict_chan['header']['Conversion Factor 00 [General Info]'].split(' ')[-1]
                data_set.quantity = chan_label
                data_set.direction = x_dir #image direction information
                data_set.data_type = 'spectrum'                

                #Add dimension info
                data_set.set_dimension(0, sid.Dimension(data_dict_chan['data']['X'],
                                                        name = 'x',
                                                        units=data_dict_chan['header']['X Amplitude [Control]'].split(' ')[-1], 
                                                        quantity = 'x',
                                                        dimension_type='spatial'))
                data_set.set_dimension(1, sid.Dimension(data_dict_chan['data']['X'],
                                                        name = 'y',
                                                        units=data_dict_chan['header']['X Amplitude [Control]'].split(' ')[-1], 
                                                        quantity='y',
                                                        dimension_type='spatial')) 
                #Writing the metadata
                data_set.metadata = data_dict_chan['header'].copy()

                #Finally, append it
                #datasets.append(data_set)
                key_channel = f"Channel_{int(channel_number):03d}"
                datasets[key_channel] = data_set
                channel_number += 1

        return datasets

    
    # read *.curves file with image and f-d curves
    #TODO: read other spectro data (*.stp and *.cur) similarly and output it in the same format as data_dict below!
    #TODO: apply Conversion Factor to final channel value. CHECK THIS EVERYWHERE!
    @staticmethod
    def _wsxm_readcurves(filepath):
        # if all_files == True: #find all channels and directions of this measurement
        #     filepath_all = wsxm_get_common_files(filepath)
        # else:
        #     filepath_all = [filepath]
        data_dict = {}
        # file_num = 1 #file number
        # for path in filepath_all:
        #     path_ext = os.path.splitext(path)[1] #file extension
        #     if path_ext == '.curves': # read *.curves spectroscopy files
        #         if all_files==True:
        #             print(file_num, os.path.basename(path)) 
        #         file_num += 1
        file = open(f'{filepath}','rb')
        header_dict_top, pos = wsxm_readheader(file)
        data_dict_chan, pos = wsxm_readimg(file, header_dict_top, pos) 
        
        data_format = header_dict_top['Image Data Type [General Info]']
        point_length, type_code  = DATA_TYPES[data_format]
        data_dict_curv = {}
        
        while True:
            # file.seek(pos, 0)
            header_dict, pos = wsxm_readheader(file, pos=pos)     
            line_pts = int(header_dict['Number of points [General Info]'])
            line_num = int(header_dict['Number of lines [General Info]'])
            y_label = header_dict['Y axis text [General Info]'].split('[')[0].strip()
            x_label = header_dict['X axis text [General Info]'].split('[')[0].strip()
            curv_ind = int(header_dict['Index of this Curve [Control]'])
            curv_num = int(header_dict['Number of Curves in this serie [Control]'])
            #CHECK THIS FOR SECOND ARRAY! MAY NOT WORK FOR 3D Mode!
            # chan_adc2v = 1#20/2**16 #adc to volt converter for 20V DSP, 16 bit resolution
            chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                chan_fact = -chan_fact
            # if y_label == 'Excitation frequency': # For frequency shift
            #     chan_offs = 0
            # else:
            chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])
            # chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])
            
            aqpt_x, aqpt_y = tuple(map(float, header_dict['Acquisition point [Control]'].replace('nm','').
                                    replace('(','').replace(')','').split(',')))
            time_f = float(header_dict['Forward plot total time [Control]'].split(' ')[0])
            time_b = float(header_dict['Backward plot total time [Control]'].split(' ')[0])
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
            # print(curv_ind, y_label)
            # plt.plot(x_data[0], y_data[0])
            # plt.plot(x_data[1], y_data[1])
            # plt.plot(data_mat[:,2], data_mat[:,3])
            # print(line_num, line_pts, line_pts*line_num)
            # plt.show()
            # x_data, y_data = np.split(ch_array[::2], 2), np.split(ch_array[1::2], 2)
            # data_dict_curv[curv_ind] = {'header': header_dict_top.copy() | header_dict.copy(), 'data': {}} #merge header dictionaries
            for j in range(int(line_num/len(line_order))):
                k = len(line_order) * j
                curv_ind_j = curv_ind + round(j/(line_num/len(line_order)), 2) if line_num > 2 else curv_ind
                data_dict_curv[curv_ind_j] = {'header': header_dict_top.copy() | header_dict.copy(), 'data': {}} #merge header dictionaries
                # data_dict[y_label]['curves'][curv_ind_j] = {'header': header_dict.copy(), 'data': {}}
                # for i, curv_dir in enumerate(line_order):
                #     print(i,j,k, k+(2*i), k+(2*i+1))
                #     data_dict[y_label]['curves'][curv_ind_j]['data'][curv_dir] = {'x': data_mat[:,k+(2*i)].max()-data_mat[:,k+(2*i)], #reverse x data
                #                                                                 'y': chan_offs+(data_mat[:,k+(2*i+1)]*chan_fact) #converted to units
                #                                                                 }
                # x_data, y_data = np.split(ch_array[k::2], 2), np.split(ch_array[k+1::2], 2)
                # x_data = ch_array[k::line_num*2], ch_array[k+2::line_num*2]
                # y_data = ch_array[k+1::line_num*2], ch_array[k+3::line_num*2]
                for i, curv_dir in enumerate(line_order):
                    # CHECK THIS WITH WSXM
                    data_dict_curv[curv_ind_j]['data'][curv_dir] = {'x': x_data[k+i].max()-x_data[k+i], #max(x_data[i])-x_data[i], #reverse x data
                                                                'y': chan_offs+(y_data[k+i]*chan_fact) #chan_offs+(y_data[i]*chan_fact) #converted to proper units
                                                            }
                                                    # 'segment':np.append(line_pts * [line_order[0]],line_pts * [line_order[1]])},
                                                    
            
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
        # if all_files == True:
        #     return data_dict
        # else: #only return the specifc data dictionary for single file if all files are not read
        #     return data_dict[y_label]['curves'][curv_ind]

    # read *.cur WSxM file
    @staticmethod
    def _wsxm_readcur(filepath):
        # if all_files == True: #find all channels and directions of this measurement
        #     filepath_all = wsxm_get_common_files(filepath)
        # else:
        #     filepath_all = [filepath]
        data_dict = {}
        # file_num = 1 #file number
        # for path in filepath_all:
        #     path_ext = os.path.splitext(path)[1] #file extension
        #     if path_ext == '.cur': # read *.curves spectroscopy files
        #         if all_files==True:
        #             print(file_num, os.path.basename(path)) 
        #         file_num += 1
        file = open(f'{filepath}','rb')
        header_dict, pos = wsxm_readheader(file)
        # data_dict_chan, pos = wsxm_readimg(file, header_dict, pos) 
        
        # data_format = header_dict['Image Data Type']
        # point_length, type_code  = DATA_TYPES[data_format]
        # data_dict_curv = {}
        
        # while True:
        # file.seek(pos, 0)
        # header_dict, pos = wsxm_readheader(file, pos=pos)
        if 'Index of this Curve [Control]' in header_dict.keys(): #for spectroscopy curves
            line_pts = int(header_dict['Number of points [General Info]'])
            line_num = int(header_dict['Number of lines [General Info]'])
            y_label = header_dict['Y axis text [General Info]'].split('[')[0].strip()
            x_label = header_dict['X axis text [General Info]'].split('[')[0].strip()
            if header_dict['Index of this Curve [Control]'] == 'Average': #for average curves
                curv_ind = header_dict['Index of this Curve [Control]']
            else:
                curv_ind = int(header_dict['Index of this Curve [Control]'])
            curv_num = int(header_dict['Number of Curves in this serie [Control]'])
            #CHECK THIS FOR SECOND ARRAY! MAY NOT WORK FOR 3D Mode!
            # chan_adc2v = 1#20/2**16 #adc to volt converter for 20V DSP, 16 bit resolution
            chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                chan_fact = -chan_fact
            # if y_label == 'Excitation frequency': # For frequency shift
            #     chan_offs = 0
            # else:
            chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])
            # chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])
            
            aqpt_x, aqpt_y = tuple(map(float, header_dict['Acquisition point [Control]'].replace('nm','').
                                    replace('(','').replace(')','').split(',')))
            time_f = float(header_dict['Forward plot total time [Control]'].split(' ')[0])
            time_b = float(header_dict['Backward plot total time [Control]'].split(' ')[0])
            
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
            aqpt_x, aqpt_y = 0, 0
            time_f = 0
            time_b = 0                
            line_order = [f'{y_label}_{ln_i+1}' for ln_i in range(line_num)] #[f'{y_label}_1', f'{y_label}_2']
        
        header_dict['Spectroscopy channel'] = y_label #Insert channel name information into dictionary
        # data_len = line_pts*line_num*2*point_length
        file.seek(pos, 0)
        data = file.read()
        data_list = []
        for ln in data.splitlines():
            ln_array = ln.decode('latin-1', errors='ignore').strip().replace('#QNAN','').split(' ')
            # print(ln_array)
            data_list.append(list(map(float,ln_array)))
        data_mat = np.array(data_list) #data matrix   
        # print(data_mat.shape)
        # ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
        # x_data, y_data = np.split(ch_array[::2], 2), np.split(ch_array[1::2], 2)
        if y_label not in data_dict.keys():
            data_dict[y_label] = {'curves':{}, 'image':{}}
        # data_dict[y_label]['curves'][curv_ind] = {'header': header_dict.copy(), 'data': {}}
        if 'Index of this Curve [Control]' in header_dict.keys(): #TODO: make "reverse data" as a function for transformation! Then eliminate if-else
            for j in range(int(line_num/len(line_order))):
                k = 2*len(line_order) * j
                curv_ind_j = curv_ind + round(j/(line_num/len(line_order)), 2) if line_num > 2 else curv_ind
                data_dict[y_label]['curves'][curv_ind_j] = {'header': header_dict.copy(), 'data': {}}
                for i, curv_dir in enumerate(line_order):
                    print(i,j,k, k+(2*i), k+(2*i+1))
                    data_dict[y_label]['curves'][curv_ind_j]['data'][curv_dir] = {'x': data_mat[:,k+(2*i)].max()-data_mat[:,k+(2*i)], #reverse x data
                                                                                'y': chan_offs+(data_mat[:,k+(2*i+1)]*chan_fact) #converted to units
                                                                                }
        else:
            data_dict[y_label]['curves'][curv_ind] = {'header': header_dict.copy(), 'data': {}}
            for i, curv_dir in enumerate(line_order):
                data_dict[y_label]['curves'][curv_ind]['data'][curv_dir] = {'x': data_mat[:,2*i], #original x data
                                                                            'y': chan_offs+(data_mat[:,2*i+1]*chan_fact) #converted to units
                                                                            }

        file.close()
        
        return data_dict, y_label
        
        # if all_files == True:
        #     return data_dict
        # else: #only return the specifc data dictionary for single file if all files are not read
        #     return data_dict[y_label]['curves'][curv_ind]


    #read *.stp spectroscopy curves. Use data_dict to update data of both approach and retract into the data dictionary
    @staticmethod
    def _wsxm_readstp(filepath, data_dict={}):
        # if all_files == True: #find all channels and directions of this measurement
        #     filepath_all = wsxm_get_common_files(filepath)
        # else:
        #     filepath_all = [filepath]
        # data_dict = {}
        # file_num = 1 #file number
        # for path in filepath_all:
        #     path_ext = os.path.splitext(path)[1] #file extension
        #     if path_ext == '.stp': # read *.stp spectroscopy files
        #         if all_files==True:
        #             print(file_num, os.path.basename(path)) 
        #         file_num += 1
        file = open(f'{filepath}','rb')
        filename = filepath.name #os.path.basename(path)
        header_dict, pos = wsxm_readheader(file)
        data_format = header_dict['Image Data Type [General Info]']
        
        # line_rate = float(header_dict['X-Frequency'].split(' ')[0])
        x_num = int(header_dict['Number of rows [General Info]'])
        y_num = int(header_dict['Number of columns [General Info]'])
        x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
        y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
        z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
        x_dir = header_dict['X scanning direction [General Info]']
        y_dir = header_dict['Y scanning direction [General Info]'] #CHECK Y DIRECTIONS
        file_dirkey = filename.split('.')[-2]
        if len(file_dirkey) == 1:
            chan_label = filename.split('_')[-1].split('.')[0] #header_dict['Acquisition channel']
            z_dir = SPECT_DICT[filename.split('.')[-2]]
        else:
            file_dirkey_match = re.search(r'line\_\d{1}', file_dirkey)
            chan_label = file_dirkey[:file_dirkey_match.start()].split('_')[-1] #header_dict['Acquisition channel']
            z_dir = SPECT_DICT[x_dir] #TODO: FIX THIS! NOT CORRECT! ALSO INVERT CONDITION ADD
            
        dsp_voltrange = float(header_dict['DSP voltage range [Miscellaneous]'].split(' ')[0])

        header_dict['Spectroscopy channel'] = chan_label #Insert channel name information into dictionary
        # print(z_dir,filename)
        # chan_fact = float(header_dict['Conversion Factor 00 [General Info]'].split(' ')[0])
        # if chan_label == 'Excitation frequency': # For frequency shift
        #     chan_offs = 0
        # else:
        #     chan_offs = float(header_dict['Conversion Offset 00 [General Info]'].split(' ')[0])

        z_data = np.linspace(0, x_len, y_num, endpoint=True) #CHECK THIS
        # print(filename,x_dir,y_dir,z_dir)
        #read binary image data
        point_length, type_code  = DATA_TYPES[data_format]
        # with open(filepath, 'rb') as file:
        file.seek(pos, 0)
        data_len = x_num*y_num*point_length
        bin_data = file.read(data_len)
        # print(data.read()[(x_num*y_num*point_length)+header_size:])
        ch_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten() 
        ch_mat = ch_array.reshape(x_num,y_num)
        if z_len == 0: #for zero data
            z_calib = 1
        else:
            # z_calib = chan_fact*dsp_voltrange/(2**16)
            z_calib = z_len/(ch_array.max()-ch_array.min()) #FIX THIS! PUT OFFSET FOR FREQ ALSO!
        
        #create separate curve data for each line (consistent with '1D' data format)
        for i in range(x_num): 
            curv_ind = i + 1        
            #data dictionary initialised in a consistant format (also check wsxm_readcurves())
            if chan_label not in data_dict.keys():
                data_dict[chan_label] = {'curves': {}, 'image':{}}
            if curv_ind not in data_dict[chan_label]['curves'].keys():
                data_dict[chan_label]['curves'][curv_ind] = {'data': {},'header': header_dict.copy()}
                #insert curve number info into header
                data_dict[chan_label]['curves'][curv_ind]['header']['Index of this Curve [Control]'] = str(curv_ind) 
                data_dict[chan_label]['curves'][curv_ind]['header']['Number of Curves in this serie [Control]'] = str(x_num)
            if z_dir not in data_dict[chan_label]['curves'][curv_ind]['data'].keys():
                data_dict[chan_label]['curves'][curv_ind]['data'][z_dir] = {}
            data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['x'] = z_data.max()-z_data #reverse x data
            data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['y'] = (z_calib*ch_mat[:][i]) #chan_offs+(ch_mat[:][i]*chan_fact)
            if x_dir == 'Forward':
                data_dict[chan_label]['curves'][curv_ind]['data'][z_dir]['y'] = np.flip((z_calib*ch_mat[:][i]))

        file.close()
        return data_dict, chan_label
  
data_file_path = '/home/pranav/Work/Data/Murcia/AFM/20240327 thiol interdigielec repeat/interdigi_thiol_newTipSi_9Nm_c_0000.f.dy.ch1'
my_reader = WSxM2DReader(data_file_path)
my_data = my_reader.read()
print(my_data.keys())
for chan_i, chandata_i in my_data.items():
    print(chan_i, chandata_i.quantity, chandata_i.direction)
    print(chandata_i.metadata['File path'])
# print(my_data['Channel_000'].metadata)
# my_data['Channel_000'].plot()
# plt.show()
