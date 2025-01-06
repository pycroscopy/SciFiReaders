import struct
import os
import re
import numpy as np
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from wsxm_analyze import convert_spectro2df, get_imgdata, get_calibdict_value, SPECT_DICT
from plot_funcs import plotly_lineplot, plotly_heatmap, fig2html, imagedf_to_excel
import transform_funcs as tsf

DATA_TYPES = {'short':(2,'h'),'short-data':(2,'h'), 'unsignedshort':(2,'H'),
              'integer-data':(4,'i'), 'signedinteger':(4,'i'),
              'float-data':(4,'f'), 'double':(8,'d')}

WSXM_CHANNEL_DICT = {'top':'Topography', 'ch1': 'Normal force', 'ch2': 'Lateral force', 
                     'ch12': 'Excitation frequency', 'ch15': 'Amplitude', 'ch16': 'Phase',
                     'adh': 'Adhesion', 'sti': 'Stiffness'
                    }

EXTRA_CHANNEL_DICT = {'Frequency shift': {'kwargs': {'pts_free': 10, #number of initial points to average to find free amplitude
                                                     'xc': 0, #x-cordinate of circle center (amp vs phase),
                                                     'ind_plot': 300, #index of circle data to be highlighted
                                                     'make_plot': False #set False to avoid plot generations (slightly faster)
                                                    },
                                          'plots': {} #circle plots stored for each curve as html for later reference/debugging
                                         }
                     }

def set_extrachan_dict(channel, param, value):
    global EXTRA_CHANNEL_DICT
    EXTRA_CHANNEL_DICT[channel]['kwargs'][param] = value

def get_extrachan_dict(channel):
    return EXTRA_CHANNEL_DICT[channel]

def wsxm_get_common_files(filepath, ext=None):
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
        path_ext_i = os.path.splitext(path_i)[1] #file extension
        if ext != None and path_ext_i != ext: #if ext given, skip files dont match the extension
            continue
        # if os.path.isfile(path_i) and i.startswith(filename_com):
        if os.path.isfile(path_i) and path_i.name.startswith(filename_com):
            files.append(path_i) 
    # print(files)
    files.remove(filepath) #make sure filepath is the first item in the list
    files.insert(0, filepath)
    return files


#read WSxM header data
def wsxm_readheader(file, pos=0, inibyte=100):
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

#read WSxM binary image data
def wsxm_readimg(file, header_dict, pos):
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
    
# Read WSxM channel image data
def wsxm_readchan(filepath, all_files=False, mute=False):
    if all_files == True: #find all channels and directions of this measurement
        filepath_all = wsxm_get_common_files(filepath)
    else:
        filepath_all = [filepath]
    data_dict = {}
    file_num = 1 #file number
    for path in filepath_all:
        path_ext = os.path.splitext(path)[1] #file extension
        if path_ext != 'gsi': #ignore *.gsi files sharing same name
            if all_files==True and mute == False:
                print(file_num, os.path.basename(path)) 
            file_num += 1
            file = open(f'{path}','rb')
            header_dict, pos = wsxm_readheader(file)
            chan_label = header_dict['Acquisition channel [General Info]']
            data_dict_chan, pos = wsxm_readimg(file, header_dict, pos)
            x_dir = header_dict['X scanning direction [General Info]']
            if chan_label in data_dict.keys():
                data_dict[chan_label][x_dir] = data_dict_chan
            else:
                data_dict[chan_label] = {}
                data_dict[chan_label][x_dir] = data_dict_chan
            file.close()
    if all_files == True:
        wsxm_calc_extrachans(data_dict, data_type='2D')
        return data_dict
    else: #only return the specifc data dictionary for single file if all files are not read
        return data_dict_chan

# read *.curves file with image and f-d curves
#TODO: read other spectro data (*.stp and *.cur) similarly and output it in the same format as data_dict below!
#TODO: apply Conversion Factor to final channel value. CHECK THIS EVERYWHERE!
def wsxm_readcurves(path):
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
    file = open(f'{path}','rb')
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
def wsxm_readcur(path):
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
    file = open(f'{path}','rb')
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
def wsxm_readstp(path, data_dict={}):
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
    file = open(f'{path}','rb')
    filename = os.path.basename(path)
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
    
    # if all_files == True:
    #     return data_dict
    # else:  #only return the specifc data dictionary for single file if all files are not read
    #     return data_dict[chan_label]['curves'][curv_ind]
    
# Read WSxM 1D spectroscopy data and curves for all available channels
def wsxm_readspectra1(filepath, all_files=False, mute=False):
    # if all_files == True: #find all channels and directions of this measurement
    filepath_all = wsxm_get_common_files(filepath)
    path_ext_f = os.path.splitext(filepath)[1]
    data_dict = {}
    data_dict_stp = {}
    file_num = 1 #file number
    for path in filepath_all:
        # print('yo', path, data_dict.keys())
        path_ext = os.path.splitext(path)[1] #file extension
        if all_files==True and mute == False:
            print(file_num, os.path.basename(path)) 
        file_num += 1
        if all_files == False and path_ext == path_ext_f: #collect all curve for the same file type (eg. approach/retract)
            if path_ext == '.curves': # read *.curves spectroscopy files
                temp_dict, chan_label = wsxm_readcurves(path)
                data_dict[chan_label] = temp_dict[chan_label].copy()
            elif path_ext == '.stp': # read *.stp spectroscopy files
                temp_dict, chan_label = wsxm_readstp(path, data_dict)#data_dict)
                # if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                # data_dict[chan_label] = temp_dict[chan_label]
            elif path_ext == '.cur': # read *.cur spectroscopy files
                temp_dict, chan_label = wsxm_readcur(path)
                # if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                data_dict[chan_label] = temp_dict[chan_label].copy()
            if path == filepath:
                chan_label_f = chan_label[:]
                curv_ind_f = list(temp_dict[chan_label_f]['curves'].keys())[0] #temp_dict[chan_label]['header']['Index of this Curve [Control]']
        elif all_files == True:
            if path_ext == '.curves': # read *.curves spectroscopy files
                temp_dict, chan_label = wsxm_readcurves(path)
                if chan_label not in data_dict.keys():
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys(): #replace with *.curves data even if it already exists (more robust)
                        data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.stp': # read *.stp spectroscopy files
                temp_dict, chan_label = wsxm_readstp(path, data_dict_stp)
                if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                            data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
            elif path_ext == '.cur': # read *.cur spectroscopy files
                temp_dict, chan_label = wsxm_readcur(path)
                if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                    data_dict[chan_label] = temp_dict[chan_label].copy()
                else:
                    for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                        if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                            data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
        # data_dict[chan_label] = temp_dict[chan_label]
        # print('hey', path, filepath)
        
    
    if all_files == True:
        wsxm_calc_extrachans(data_dict, data_type='1D')
        return data_dict
    else:  #only return the specifc data dictionary for single file if all files are not read
        return data_dict[chan_label_f]['curves'][curv_ind_f]

# Read WSxM 1D spectroscopy data and curves for all available channels
def wsxm_readspectra(filepath, all_files=False, mute=False):
    # if all_files == True: #find all channels and directions of this measurement
    if all_files == True:
        filepath_all = wsxm_get_common_files(filepath)
    else:
        file_ext = os.path.splitext(filepath)[1] #file extension
        filepath_all = wsxm_get_common_files(filepath, ext=file_ext) #collect all curve for the same file type (eg. approach/retract)
    data_dict = {}
    data_dict_stp = {}
    file_num = 1 #file number
    for path in filepath_all:
        # print('yo', path, data_dict.keys())
        path_ext = os.path.splitext(path)[1] #file extension
        if mute == False:
            print(file_num, os.path.basename(path)) 
        file_num += 1
        # if all_files == False and path_ext == path_ext_f: #collect all curve for the same file type (eg. approach/retract)
        #     if path_ext == '.curves': # read *.curves spectroscopy files
        #         temp_dict, chan_label = wsxm_readcurves(path)
        #         data_dict[chan_label] = temp_dict[chan_label].copy()
        #     elif path_ext == '.stp': # read *.stp spectroscopy files
        #         temp_dict, chan_label = wsxm_readstp(path, data_dict)#data_dict)
        #         # if chan_label not in data_dict.keys(): #ignore data if *.curves already found
        #         # data_dict[chan_label] = temp_dict[chan_label]
        #     elif path_ext == '.cur': # read *.cur spectroscopy files
        #         temp_dict, chan_label = wsxm_readcur(path)
        #         # if chan_label not in data_dict.keys(): #ignore data if *.curves already found
        #         data_dict[chan_label] = temp_dict[chan_label].copy()
        #     if path == filepath:
        #         chan_label_f = chan_label[:]
        #         curv_ind_f = list(temp_dict[chan_label_f]['curves'].keys())[0] #temp_dict[chan_label]['header']['Index of this Curve [Control]']
        # elif all_files == True:
        if path_ext == '.curves': # read *.curves spectroscopy files
            temp_dict, chan_label = wsxm_readcurves(path)
            if chan_label not in data_dict.keys():
                data_dict[chan_label] = temp_dict[chan_label].copy()
            else:
                for curv_ind_i in temp_dict[chan_label]['curves'].keys(): #replace with *.curves data even if it already exists (more robust)
                    data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
        elif path_ext == '.stp': # read *.stp spectroscopy files
            temp_dict, chan_label = wsxm_readstp(path, data_dict_stp)
            if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                data_dict[chan_label] = temp_dict[chan_label].copy()
            else:
                for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                    if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                        data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
        elif path_ext == '.cur': # read *.cur spectroscopy files
            temp_dict, chan_label = wsxm_readcur(path)
            if chan_label not in data_dict.keys(): #ignore data if *.curves already found
                data_dict[chan_label] = temp_dict[chan_label].copy()
            else:
                for curv_ind_i in temp_dict[chan_label]['curves'].keys():
                    if curv_ind_i not in data_dict[chan_label]['curves'].keys():
                        data_dict[chan_label]['curves'][curv_ind_i] = temp_dict[chan_label]['curves'][curv_ind_i].copy()
        # data_dict[chan_label] = temp_dict[chan_label]
        # print('hey', path, filepath)
        if path == filepath:
            chan_label_f = chan_label[:]
            curv_ind_f = list(temp_dict[chan_label_f]['curves'].keys())[0] #temp_dict[chan_label]['header']['Index of this Curve [Control]']

        
    
    if all_files == True:
        wsxm_calc_extrachans(data_dict, data_type='1D')
        return data_dict
    else:  #only return the specifc data dictionary for single file if all files are not read
        return data_dict[chan_label_f]['curves'][curv_ind_f]

# Read WSxM Force volume data
def wsxm_readforcevol(filepath, all_files=False, topo_only=False, mute=False):
    if all_files == True: #find all channels and directions of this measurement
        filepath_all = wsxm_get_common_files(filepath)
    else:
        filepath_all = [filepath]
    data_dict = {}
    file_num = 1 #file number
    for path in filepath_all:
        path_ext = os.path.splitext(path)[1] #file extension
        # if path_ext == '.top': #topgraphy data
        #     data_dict['Topography'] = wsxm_readchan(path)
        if path_ext == '.gsi': #force volume data from *.gsi files
            if mute==False:
                print(file_num, os.path.basename(path)) 
            file_num += 1
            file = open(f'{path}','rb')
            header_dict, pos = wsxm_readheader(file)
            
            data_format = header_dict['Image Data Type [General Info]']
            chan_label = header_dict['Acquisition channel [General Info]']
            spec_dir = header_dict['Spectroscopy type [General Info]']
            x_dir = spec_dir.split(' ')[1]
            y_dir = header_dict['Y scanning direction [General Info]'] #CHECK Y DIRECTIONS
            # z_dir = SPECT_DICT[spec_dir.split(' ')[3]]
            line_rate = float(header_dict['X-Frequency [Control]'].split(' ')[0])
            x_num = int(header_dict['Number of rows [General Info]'])
            y_num = int(header_dict['Number of columns [General Info]'])
            chan_num = int(header_dict['Number of points per ramp [General Info]'])
            x_len = float(header_dict['X Amplitude [Control]'].split(' ')[0])
            y_len = float(header_dict['Y Amplitude [Control]'].split(' ')[0])
            z_len = float(header_dict['Z Amplitude [General Info]'].split(' ')[0])
            chan_adc2v = float(header_dict['ADC to V conversion factor [General Info]'].split(' ')[0])
            
            if chan_label == 'Excitation frequency': # For frequency shift
                chan_fact = float(header_dict['Conversion factor 0 for input channel [General Info]'].split(' ')[0])
                chan_offs = float(header_dict['Conversion offset 0 for input channel [General Info]'].split(' ')[0]) #0
            else:
                chan_fact = 1
                chan_offs = 0

            chan_inv = header_dict['Channel is inverted [General Info]']
            if chan_inv == 'Yes':
                chan_fact = -chan_fact
                # chan_offs = float(header_dict['Conversion offset 0 for input channel [General Info]'].split(' ')[0])
            # chan_offs = float(header_dict['Conversion offset 0 for input channel [General Info]'].split(' ')[0])
                    
            x_data = np.linspace(x_len, 0, x_num, endpoint=True) #if x_dir == 'Backward' else np.linspace(x_len, 0, x_num, endpoint=True)
            y_data = np.linspace(0, y_len, y_num, endpoint=True) #if y_dir == 'Down' else np.linspace(y_len, 0, y_num, endpoint=True)
            # xx_data, yy_data = np.meshgrid(x_data, y_data)
        
            z_data = np.empty(0)
            for i in range(chan_num):
                z_data = np.append(z_data, float(header_dict[f'Image {i:03} [Spectroscopy images ramp value list]'].split(' ')[0]))
            # if z_dir == 'retract':
            z_data = np.flip(z_data) #reverse z data order to make zero as point of contact
            
            #read binary image data
            point_length, type_code  = DATA_TYPES[data_format]
            # with open(filepath, 'rb') as file:
            file.seek(pos, 0)
            data_len = x_num*y_num*point_length
            # pos += data_len #skip first topo image
            #read first topography data
            bin_data = file.read(data_len)
            topo_array = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
            if z_len == 0: #for zero data
                topo_calib = 1
            else:
                topo_calib = z_len/(topo_array.max()-topo_array.min())
            #topo data dictionary
            data_dict_topo = {'data': {'Z': topo_calib*topo_array.reshape(x_num, y_num),
                                       'X': x_data,
                                       'Y': y_data
                                       },
                              'header': header_dict}
            topo_label = 'Topography'
            
            if topo_only == True and all_files == False: #return only topo data dictionary
                file.close()
                return data_dict_topo
                
            if topo_label not in data_dict.keys():
                data_dict[topo_label] = {}
            data_dict[topo_label][spec_dir] = data_dict_topo
            
            if topo_only == False: #skip channel read if topo_only=True
                pos += data_len
                ch_array = np.empty(0) #initialize channel data array
                for i in range(1, chan_num+1):
                    file.seek(pos, 0)
                    bin_data = file.read(data_len)
                    # print(data.read()[(x_num*y_num*point_length)+header_size:])
                    ch_array_temp = np.array(list(struct.iter_unpack(f'{type_code}', bin_data))).flatten()
                    # print(ch_array_temp.min(), ch_array_temp.max())
                    # if i == 0:
                    #     z_calib = z_len/(ch_array_temp.max()-ch_array_temp.min())
                    # else:
                    ch_array = np.append(ch_array, chan_offs+(ch_array_temp*chan_adc2v*chan_fact))
                    pos += data_len #next image
                # print(z_calib, chan_adc2v, z_len)
                
                #img data dictionary
                data_dict_chan = {'data': {'ZZ': ch_array.reshape(chan_num,y_num,x_num),#(x_num,y_num,chan_num),
                                           'X': x_data,
                                           'Y': y_data,
                                           'Z': z_data
                                          },
                                  'header': header_dict}
                if chan_label not in data_dict.keys():
                    data_dict[chan_label] = {}
                data_dict[chan_label][spec_dir] = data_dict_chan
            file.close()
        
        # pos += data_len #bytes read so far  
    wsxm_calc_extrachans(data_dict, data_type='3D')
    return data_dict

# add additional channels to data_dict
def wsxm_calc_extrachans(data_dict, data_type):
    global EXTRA_CHANNEL_DICT
    channels = data_dict.keys()
    #Include into data_dict true amplitude and true phase from the "amplitude" and "phase" channels, 
    #which are in-fact the quadrature and in-phase outputs, respectively,of the lock-in amplifier
    if all(chan in channels for chan in ['Amplitude', 'Phase']) == True:
        amp_data = data_dict['Amplitude']
        phase_data = data_dict['Phase']
        data_dict['True Amplitude'] = {}
        data_dict['True Phase'] = {}
        if data_type == '1D':
            data_dict['True Amplitude']['curves'] = {}
            data_dict['True Phase']['curves'] = {}
            for amp_i, phase_i in zip(amp_data['curves'].items(), phase_data['curves'].items()):
                data_dict['True Amplitude']['curves'][amp_i[0]] = {'data':{'approach':{'x':amp_i[1]['data']['approach']['x'],
                                                                                       'y':tsf.hypotenuse(amp_i[1]['data']['approach']['y'],
                                                                                                          phase_i[1]['data']['approach']['y'])
                                                                                      },
                                                                           'retract':{'x':amp_i[1]['data']['retract']['x'],
                                                                                      'y':tsf.hypotenuse(amp_i[1]['data']['retract']['y'],
                                                                                                         phase_i[1]['data']['retract']['y'])
                                                                                     }
                                                                          },
                                                                   'header':amp_i[1]['header']
                                                                  }
                
                data_dict['True Phase']['curves'][phase_i[0]] = {'data':{'approach':{'x':phase_i[1]['data']['approach']['x'],
                                                                                   'y':np.arctan2(amp_i[1]['data']['approach']['y'],
                                                                                                  phase_i[1]['data']['approach']['y'])
                                                                                      },
                                                                       'retract':{'x':phase_i[1]['data']['retract']['x'],
                                                                                  'y':np.arctan2(amp_i[1]['data']['retract']['y'],
                                                                                                 phase_i[1]['data']['retract']['y'])
                                                                                     }
                                                                          },
                                                               'header':phase_i[1]['header']
                                                              }
        elif data_type == '2D':
            for amp_i, phase_i in zip(amp_data.items(), phase_data.items()):
                img_dir = amp_i[0]
                data_dict['True Amplitude'][img_dir] = {'data': {'X':amp_i[1]['data']['X'],
                                                                 'Y':amp_i[1]['data']['Y'],
                                                                 'Z':tsf.hypotenuse(amp_i[1]['data']['Z'],
                                                                                    phase_i[1]['data']['Z'])},
                                                        'header':amp_i[1]['header']
                                                       }

                data_dict['True Phase'][img_dir] = {'data': {'X':phase_i[1]['data']['X'],
                                                             'Y':phase_i[1]['data']['Y'],
                                                             'Z':np.arctan2(amp_i[1]['data']['Z'],
                                                                            phase_i[1]['data']['Z'])},
                                                    'header':phase_i[1]['header']
                                                   }

        elif data_type == '3D':
            for amp_i, phase_i in zip(amp_data.items(), phase_data.items()):
                img_dir = amp_i[0]
                data_dict['True Amplitude'][img_dir] = {'data': {'X':amp_i[1]['data']['X'],
                                                                 'Y':amp_i[1]['data']['Y'],
                                                                 'Z':amp_i[1]['data']['Z'],
                                                                 'ZZ':tsf.hypotenuse(amp_i[1]['data']['ZZ'],
                                                                                     phase_i[1]['data']['ZZ'])},
                                                        'header':amp_i[1]['header']
                                                       }

                data_dict['True Phase'][img_dir] = {'data': {'X':phase_i[1]['data']['X'],
                                                             'Y':phase_i[1]['data']['Y'],
                                                             'Z':phase_i[1]['data']['Z'],
                                                             'ZZ':np.arctan2(amp_i[1]['data']['ZZ'],
                                                                             phase_i[1]['data']['ZZ'])},
                                                    'header':phase_i[1]['header']
                                                   }
    # else:
    #     chan_missing = ['Amplitude', 'Phase'][list(chan in channels for chan in ['Amplitude', 'Phase']).index(False)]
    #     print(f'True Amplitude/Phase channels not created due to missing channel: {chan_missing}')
     
    # add normal deflection channel, to be calibrated in length units
    if 'Normal force' in channels:
        data_dict['Normal deflection'] = dict(data_dict['Normal force']) #deep copy of normal force channel
    #add channel showing distance between the tip's upper amplitude peak and sample (closest distance)
    if all(c in channels for c in ['Normal deflection', 'Amplitude']) == True and data_type in ['1D', '3D']:
        if 'True Amplitude' in channels: #choose true amplitude channel if it exists. Otherwise use Amplitude channel (NOT RELIABLE!)
            data_dict['Amplitude-sample distance'] = dict(data_dict['True Amplitude'])
        else:
            data_dict['Amplitude-sample distance'] = dict(data_dict['Amplitude'])
    #add channel showing sample deformation
    if 'Normal deflection' in channels and data_type in ['1D', '3D']:
        data_dict['Sample deformation'] = dict(data_dict['Normal deflection'])

    if all(c in channels for c in ['Amplitude', 'Phase', 'Excitation frequency']) == True and data_type in ['1D']:
        amp_data = data_dict['Amplitude']
        phase_data = data_dict['Phase']
        freq_data= data_dict['Excitation frequency']
        # header = spectro_data_ini['Excitation frequency']['curves'][curv_ind]['header']
        data_dict['Amplitude dissipated']= {}
        data_dict['Energy dissipated'] = {}
        data_dict['Frequency shift'] = {}
        data_dict['Amplitude dissipated']['curves'] = {}
        data_dict['Energy dissipated']['curves'] = {}
        data_dict['Frequency shift']['curves'] = {}
        
        pts_free = EXTRA_CHANNEL_DICT['Frequency shift']['kwargs']['pts_free'] #10 #number of "free amplitude" points to average
        ind_plot = EXTRA_CHANNEL_DICT['Frequency shift']['kwargs']['ind_plot'] #index of data to save plot
        make_plot = EXTRA_CHANNEL_DICT['Frequency shift']['kwargs']['make_plot'] #make plot
        
        def circle(center, radius, theta_range):   
            theta = np.linspace(theta_range[0], theta_range[1], 1000)
            x = center[0] + radius * np.cos(theta)
            y = center[1] + radius * np.sin(theta)
            return x, y, theta
        
        # Function to find the intersection point on the circle
        # def find_intersection(center, radius, point):
        #     h, k = center
        #     dx, dy = point # Direction vector from center to the point     
        #     # Calculate the distance from the center to the point
        #     distance = np.sqrt(dx**2 + dy**2)
        #     cos_theta = dy/distance
        #     chord_length = 2*radius*cos_theta             
        #     # Normalize the direction vector to unit length
        #     dx /= distance
        #     dy /= distance            
        #     # Scale the direction vector by the radius of the circle
        #     dx *= chord_length#radius
        #     dy *= chord_length#radius           
        #     # Calculate the intersection point
        #     intersection_x = -dx # + h
        #     intersection_y = -dy # + k 
        #     return (intersection_x, intersection_y)
        def find_intersection(center, radius, point):
            xc, yc = center[0], center[1]
            rc = radius
            xp, yp = point[0], point[1]
            # Direction vector of the line from origin to (xp, yp)
            D = np.array([xp, yp])            
            # Coefficients of the quadratic equation
            a = xp**2 + yp**2
            b = -2 * (xp * xc + yp * yc)
            c = xc**2 + yc**2 - rc**2
            
            # Solve the quadratic equation
            discriminant = b**2 - 4 * a * c
            if discriminant < 0:
                return (0, 0)  # No real intersection (line does not intersect the circle)            
            sqrt_discriminant = np.sqrt(discriminant)
            t1 = (-b + sqrt_discriminant) / (2 * a)
            t2 = (-b - sqrt_discriminant) / (2 * a)
            
            # Calculate intersection points
            I1 = t1 * D
            I2 = t2 * D
            if I1[1] <= 0:
                return I1
            else:
                return I2
                
        for amp_i, phase_i, freq_i in zip(amp_data['curves'].items(), phase_data['curves'].items(), freq_data['curves'].items()):
            amp_data_app = amp_i[1]['data']['approach']['y']
            phase_data_app = phase_i[1]['data']['approach']['y']
            # freq_data_app = freq_i[1]['data']['approach']['y']
            if 'Resonance frequency [Dynamic settings]' in freq_i[1]['header'].keys(): #CHECK! ONLY WORKS FOR *.curves FILE!
                drive_freq = float(freq_i[1]['header']['Resonance frequency [Dynamic settings]'].split(' ')[0]) #cantilever drive freq
            else:
                drive_freq = 0
            res_freq = get_calibdict_value('Resonance frequency', 'Hz')['factor']
            #res_freq = float(freq_i[1]['header']['Resonance frequency [Dynamic settings]'].split(' ')[0]) #cantilever free resonance freq
            # q_fac = float(freq_i[1]['header']['Quality factor (Q) [Dynamic settings]']) #GET THESE FROM CALIB_DICT from thermal tune!
            q_fac = get_calibdict_value('Quality factor', '')['factor']
            k_cant = get_calibdict_value('Spring constant', 'N/m')['factor'] #cantilever spring constant
            mass_cant = k_cant/(4*(np.pi*res_freq)**2) #cantilever mass
            #use approach data to find lockin output complex plane circle (amp vs phase)
            amp_free = np.mean(amp_data_app[:pts_free]) #average first 10 points to get initial "free" amplitude
            # amptrue_min = np.mean(data_amptrue[:pts_free])
            # r = np.mean(np.sqrt(amp_data_app[:pts_free]**2 + phase_data_app[:pts_free]**2))/2
            # r0 = -r
            # print(amp_free)
            # fig = plt.figure()
            # ax = fig.add_subplot(111,aspect='equal')  
            
            # phis=np.arange(0,6.28,0.01)
            # r = abs(amp_free)/2
            # r0 = amp_free/2
            center = (EXTRA_CHANNEL_DICT['Frequency shift']['kwargs']['xc'],amp_free/2)
            r = np.mean(np.sqrt((amp_data_app[:pts_free]-center[1])**2 + (phase_data_app[:pts_free]-center[0])**2))
            circ_x, circ_y, circ_theta = circle(center=center, radius=r, theta_range=(-np.pi/2, -3*np.pi/2))

            if make_plot == True:
                plt.axhline(y=0, linewidth=1, alpha=0.7)
                plt.axvline(x=0, linewidth=1, alpha=0.7)
                plt.plot(phase_data_app, amp_data_app, 'y.')
                plt.plot(circ_x, circ_y, 'r--')
                plt.plot(*center, '*r')
            
            freq_shift = {}
            amp_diss = {}
            # phase_ang = {}
            energy_diss = {}
            for dir_i in amp_i[1]['data'].keys():
                freq_shift[dir_i] = []
                amp_diss[dir_i] = []
                # phase_ang[dir_i] = []
                amp_data_i = amp_i[1]['data'][dir_i]['y']
                phase_data_i = phase_i[1]['data'][dir_i]['y']
                freq_data_i = freq_i[1]['data'][dir_i]['y']
                # ind_plot = 320 #point to plot to check
                for data_ind in range(len(amp_data_i)):
                    data_pt = (phase_data_i[data_ind], amp_data_i[data_ind])
                    inter_pt = find_intersection(center=center, radius=r, point=data_pt)
                    # cos_theta = data_pt[1]/np.sqrt(data_pt[0]**2 + data_pt[1]**2)
                    # print(data_pt, inter_pt, np.arctan2(inter_pt[1]-center[1],inter_pt[0])*180/np.pi)   
                    ampdiff_pt = amp_free**2 - (data_pt[0]**2 + data_pt[1]**2) # ONLY FOR PLL ON! CHANGE OR REMOVE THIS!! BELOW IS MORE CORRECT
                    freq_pt = freq_data_i[data_ind] #CHECK!
                    if inter_pt[0] == 0 or data_pt[1] >= 0:
                        # freq_shift[dir_i].append(0) #UNCOMMMENT THIS
                        freq_shift[dir_i].append(drive_freq-freq_pt) #CHECK THIS!!
                        # freq_shift[dir_i].append(res_freq-freq_pt)
                        # amp_diss[dir_i].append(0) #UNCOMMMENT THIS
                        if ampdiff_pt >= 0: #COMMENT THIS
                            amp_diss[dir_i].append(np.sqrt(ampdiff_pt))
                        else:
                            amp_diss[dir_i].append(-np.sqrt(-ampdiff_pt))
                        # phase_ang_pt = -90
                        # phase_ang.append(phase_ang_pt)
                    else:
                        #UNCOMMENT THIS
                        # ampdiff_pt = (inter_pt[0]**2 + inter_pt[1]**2) - (data_pt[0]**2 + data_pt[1]**2) #square difference of amp (energy bal.)
                        if ampdiff_pt >= 0:
                            amp_diss[dir_i].append(np.sqrt(ampdiff_pt))
                        else:
                            amp_diss[dir_i].append(-np.sqrt(-ampdiff_pt))
                        phase_pt = inter_pt[1]/inter_pt[0]
                        # phase_ang_pt = np.arctan2(inter_pt[1],inter_pt[0])*180/np.pi
                        # phase_ang.append(phase_ang_pt)
                        inter_ind = np.argmin(abs(circ_y-inter_pt[1]))
                        # freq_pt = freq_data_i[data_ind] #*freq_sens*1000 drive_freq - 
                        # print(inter_pt[1], circ_y[inter_ind])
                        freq_shift[dir_i].append(drive_freq-freq_pt) #CHECK THIS!!
                        # freq_shift[dir_i].append(res_freq-freq_pt) #ONLY FOR PLL ON! CHANGE THIS! BELOW IS MORE CORRECT, UNCOMMENT!
                        # if phase_pt >= 0 : #calculate shift in resonance frequency
                        #     freq_calc = res_freq - (freq_pt/(2*q_fac*phase_pt))*(np.sqrt(1+(4*(q_fac**2)*(phase_pt**2)))-1)
                        #     freq_shift[dir_i].append(freq_calc) #attractive freq shift considered positive
                        # else:
                        #     freq_calc = res_freq - (freq_pt/(2*q_fac*phase_pt))*(-np.sqrt(1+(4*(q_fac**2)*(phase_pt**2)))-1)
                        #     freq_shift[dir_i].append(freq_calc) #attractive freq shift considered positive
                
                    if data_ind == ind_plot and dir_i == 'approach' and make_plot == True:
                        inter_pt_plot = inter_pt[0], inter_pt[1]
                        data_pt_plot = data_pt[0], data_pt[1]
                        plt.plot([0, inter_pt_plot[0]], [0, inter_pt_plot[1]], 'w:')
                        plt.plot(*inter_pt_plot, 'wo')
                        plt.plot(*data_pt_plot, 'wo')                        
                        plt.gca().minorticks_on()
                        plt.grid(True, alpha=0.3, which='both')
                        EXTRA_CHANNEL_DICT['Frequency shift']['plots'][amp_i[0]] = fig2html(plt.gcf(), plot_type='matplotlib',
                                                                                           width=500, height=500, dpi=300)
                    plt.clf()
                    plt.close('all')
                        # print(phase_ang_pt, ampdiff_pt, amptrue_min - ampdiff_pt)
                        # print(data_pt, inter_pt)
                        # if freq_calc < 0:
                        #     print(data_ind, data_pt, freq_calc, data_x[data_ind])
                    # print(freq_shift, freq_calc)
                
                # print(cali_fact) drive_freq-
                energy_diss[dir_i] =  mass_cant*(np.pi**2)*np.square(amp_diss[dir_i])*(np.square(freq_data_i)+\
                                                                                       np.square(res_freq-np.array(freq_shift[dir_i]))) #dissipation energy
            
            data_dict['Amplitude dissipated']['curves'][amp_i[0]] = {'data':{'approach':{'x': amp_i[1]['data']['approach']['x'],
                                                                                         'y': np.array(amp_diss['approach'])
                                                                                      },
                                                                           'retract':{'x': amp_i[1]['data']['retract']['x'],
                                                                                      'y': np.array(amp_diss['retract'])
                                                                                     }
                                                                          },
                                                                     'header':amp_i[1]['header']
                                                                     }
            data_dict['Energy dissipated']['curves'][amp_i[0]] = {'data':{'approach':{'x': amp_i[1]['data']['approach']['x'],
                                                                                      'y': energy_diss['approach']
                                                                                      },
                                                                           'retract':{'x': amp_i[1]['data']['retract']['x'],
                                                                                      'y': energy_diss['retract']
                                                                                     }
                                                                          },
                                                                  'header':amp_i[1]['header']
                                                                  }
            data_dict['Frequency shift']['curves'][freq_i[0]] = {'data':{'approach':{'x': freq_i[1]['data']['approach']['x'],
                                                                                     'y': np.array(freq_shift['approach'])
                                                                                      },
                                                                         'retract':{'x': freq_i[1]['data']['retract']['x'],
                                                                                    'y': np.array(freq_shift['retract'])
                                                                                    }
                                                                         },
                                                                 'header':freq_i[1]['header']
                                                                 }
            
            # amp_true_diss = np.sqrt(np.abs(np.square(amptrue_min)-np.square(data_amptrue)))
    
        
    # else:
    #     print(f'Normal deflection channel not created due to missing channel: Normal force')

#reads all wsxm data files in a folder, collects them into a table with thumbnails and file metadata information for browsing.
#saved the table as a binary and excel file in the folder. The binary file can be later loaded directly to avoid reading all the files again.
#"refresh" parameter can be used to search the directory again for file and replace existing pickle/excel file list
# def wsxm_collect_files(folderpath, refresh=False):
#     # folderpath = 'data/'
#     # folderpath = filedialog.askdirectory() #use folder picker dialogbox
#     picklepath = f"{folderpath}/filelist_{os.path.basename(folderpath)}.pkl" #pickled binary file
#     if os.path.exists(picklepath) and refresh==False:
#         file_df = pd.read_pickle(picklepath) #choose "datalist.pkl" file (faster)
#     else:
#         file_dict = {'plot': [], 'file':[], 'name': [], 'channel': [], 'type': [], #'mode': [], 
#                      'feedback': [], 'size':[], 'resolution':[], 'time':[]}
#         for filename_i in os.listdir(folderpath):
#             path_i = os.path.join(folderpath,filename_i)
#             if os.path.isfile(path_i):
#                 match_i = re.search(r'\_\d{4}', filename_i) #regex to find 4 digit number in filename
#                 time_i = datetime.datetime.fromtimestamp(os.path.getmtime(path_i)) #time of file modified (from file metadata)
#                 path_ext_i = os.path.splitext(path_i)[1] #file extension
#                 if path_ext_i in ['.pkl','.xlsx','.txt']: #ignore pickle and excel and other files
#                     continue
#                 if match_i != None:
#                     # print(datetime.datetime.now().strftime("%H:%M:%S"), filename_i)
#                     filename_com_i = filename_i[:match_i.start()+5]
#                     if path_ext_i == '.gsi':
#                         data_type_i = '3D'
#                         channel_i = 'Topography' #only check topo image for force volume data
#                         feedback_i = ''
                        
#                         data_dict_chan_i = wsxm_readforcevol(path_i, all_files=False, topo_only=True)
#                         header_i = data_dict_chan_i['header']
#                         # print(header_i)
#                         z_pts_i = int(header_i['Number of points per ramp'])
#                         z_extrema_i = [float(header_i[f'Image {z_pts_i-1:03}'].split(' ')[0]),
#                                        float(header_i['Image 000'].split(' ')[0])]
#                         res_i = header_i['Number of columns'] + 'x' + header_i['Number of columns'] + 'x' + header_i['Number of points per ramp']
#                         size_i = header_i['X Amplitude'] + ' x ' + header_i['Y Amplitude'] + ' x ' + f'{int(max(z_extrema_i))}' + ' ' + header_i['Image 000'].split(' ')[1]
#                         xx_i, yy_i, zz_i = get_imgdata(data_dict_chan_i)
#                         plt.pcolormesh(xx_i, yy_i, zz_i, cmap='afmhot')
#                         plt.axis('off')
#                         fig_i = fig2html(plt.gcf())
#                         plt.close()
#                     elif path_ext_i in ['.curve']: #TODO: *.curve also combine to below condition!
#                         data_type_i = '1D'
#                         channel_i = filename_i[match_i.start()+6:].split('.')[0].split('_')[0]
#                         fig_i = ''
#                         res_i = ''
#                         size_i = ''
#                         feedback_i = ''
#                     elif path_ext_i in ['.curves', '.stp', '.cur']:
#                         data_type_i = '1D'
#                         channel_i = filename_i[match_i.start()+6:].split('.')[0].split('_')[0]
#                         feedback_i = ''
#                         data_dict_chan_i = wsxm_readspectra(path_i, all_files=False)
#                         spec_dir_i = list(data_dict_chan_i['data'].keys())
#                         header_i = data_dict_chan_i['header']
#                         if path_ext_i == '.stp':                            
#                             res_i = header_i['Number of columns']
#                             size_i = header_i['X Amplitude']
#                         else: #for *.curves and *.cur
#                             res_i = header_i['Number of points']
#                             size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit']
#                         # if path_ext_i == '.curves':
#                         #     data_dict_chan_i = wsxm_readcurves(path_i, all_files=False)
#                         #     header_i = data_dict_chan_i['header']
#                         #     res_i = header_i['Number of points']
#                         #     spec_dir_i = list(data_dict_chan_i['data'].keys())
#                         #     size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit']
#                         # elif path_ext_i == '.cur':
#                         #     data_dict_chan_i = wsxm_readcur(path_i, all_files=False)
#                         #     header_i = data_dict_chan_i['header']
#                         #     res_i = header_i['Number of points']
#                         #     spec_dir_i = list(data_dict_chan_i['data'].keys())
#                         #     size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit']
#                         # elif path_ext_i == '.stp':
#                         #     data_dict_chan_i = wsxm_readstp(path_i, all_files=False)
#                         #     header_i = data_dict_chan_i['header']
#                         #     res_i = header_i['Number of columns']
#                         #     spec_dir_i = list(data_dict_chan_i['data'].keys())
#                         #     size_i = header_i['X Amplitude']
#                         spectrodf_i = convert_spectro2df(data_dict_chan_i['data'])
#                         sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
#                         fig_i = fig2html(plt.gcf())
#                         plt.close()
#                     else:
#                         data_type_i = '2D'
#                         channel_i = WSXM_CHANNEL_DICT[path_ext_i[1:]]
#                         file_tags_i = filename_i[match_i.start()+6:].split('.')
                        
#                         data_dict_chan_i = wsxm_readchan(path_i, all_files=False)
#                         header_i = data_dict_chan_i['header']
#                         res_i = header_i['Number of rows'] + 'x' + header_i['Number of columns']
#                         size_i = header_i['X Amplitude'] + ' x ' + header_i['Y Amplitude']
#                         feedback_i = header_i['Input channel']
#                         xx_i, yy_i, zz_i = get_imgdata(data_dict_chan_i)
#                         plt.pcolormesh(xx_i, yy_i, zz_i, cmap='afmhot')
#                         plt.axis('off')
#                         fig_i = fig2html(plt.gcf())
#                         plt.close()
#                 else: #if no match for 4 digit counter found in file name
#                     if path_ext_i == '.cur': #read other *.cur file e.g. tuning
#                         filename_com_i = filename_i[:-4]
#                         data_type_i = '1D'
#                         channel_i = 'Other'
#                         data_dict_chan_i = wsxm_readspectra(path_i, all_files=False)
#                         header_i = data_dict_chan_i['header']
#                         res_i = header_i['Number of points']
#                         spec_dir_i = list(data_dict_chan_i['data'].keys())
#                         size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit']
#                         feedback_i = ''
#                         spectrodf_i = convert_spectro2df(data_dict_chan_i['data'])
#                         sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
#                         fig_i = fig2html(plt.gcf())
#                         plt.close()
    
#                 file_dict['file'].append(filename_com_i)
#                 file_dict['name'].append(filename_i)
#                 file_dict['channel'].append(channel_i)
#                 file_dict['type'].append(data_type_i)
#                 file_dict['size'].append(size_i)
#                 file_dict['resolution'].append(res_i)
#                 file_dict['feedback'].append(feedback_i)
#                 file_dict['plot'].append(fig_i)
#                 file_dict['time'].append(time_i)
        
#         file_df = pd.DataFrame.from_dict(file_dict)

#         #save "pickled" binary data of file list for later use
#         file_df.to_pickle(f"{folderpath}/filelist_{os.path.basename(folderpath)}.pkl")
#         #save excel file for manual check
#         file_df.drop(columns=['plot']).to_excel(f"{folderpath}/filelist_{os.path.basename(folderpath)}.xlsx")
    
#     return file_df


#reads all wsxm data files in a folder, collects them into a table with thumbnails and file metadata information for browsing.
#saved the table as a binary and excel file in the folder. The binary file can be later loaded directly to avoid reading all the files again.
#"refresh" parameter can be used to search the directory again for file and replace existing pickle/excel file list
def wsxm_collect_files(folderpath, refresh=False, flatten_chan=[], make_plot=True):
    # folderpath = 'data/'
    # folderpath = filedialog.askdirectory() #use folder picker dialogbox
    # picklepath = f"{folderpath}/filelist_{os.path.basename(folderpath)}.pkl" #pickled binary file
    # print(folderpath)
    picklepath = folderpath / f"filelist_{folderpath.name}.pkl" #pickled binary file
    if os.path.exists(picklepath) and refresh==False:
        file_df = pd.read_pickle(picklepath) #choose "datalist.pkl" file (faster)
    else:
        file_dict = {'plot': [], 'file':[], 'name': [], 'channel': [], 'type': [], #'feedback': [], #'mode': [], 
                     'size':[], 'resolution':[], 'max':[], 'min':[], 'avg':[], 'time':[], 
                     'extension':[], 'header': [], 'header names':[]}
        # for fnum_i, filename_i in enumerate(os.listdir(folderpath)):
        for fnum_i, path_i in enumerate(folderpath.iterdir()):
            filename_i = path_i.name
            print(fnum_i, filename_i)
            # path_i = os.path.join(folderpath,filename_i)
            if os.path.isfile(path_i):
                match_i = re.search(r'\_\d{4}', filename_i) #regex to find 4 digit number in filename
                time_i = datetime.datetime.fromtimestamp(os.path.getmtime(path_i)) #time of file modified (from file metadata)
                path_ext_i = os.path.splitext(path_i)[1] #file extension
                if path_ext_i in ['.pkl','.xlsx','.txt', '.psdata', '.xlsx#', '.wsxm', '.MOV']: #ignore pickle and excel and other files
                    continue #TODO: make a good filter to avoid other files than raw WSxM files
                if match_i != None:
                    # print(datetime.datetime.now().strftime("%H:%M:%S"), filename_i)
                    filename_com_i = filename_i[:match_i.start()+5]
                    if path_ext_i == '.gsi':
                        data_type_i = '3D'
                        # channel_i = 'Topography' #only check topo image for force volume data
                        # feedback_i = ''
                        #Topo channel only taken for image display
                        data_dict_chan_i = wsxm_readforcevol(path_i, all_files=False, topo_only=True, mute=True)
                        header_i = data_dict_chan_i['header']
                        channel_i = header_i['Acquisition channel [General Info]']
                        # print(header_i)
                        z_pts_i = int(header_i['Number of points per ramp [General Info]'])
                        z_extrema_i = [float(header_i[f'Image {z_pts_i-1:03} [Spectroscopy images ramp value list]'].split(' ')[0]),
                                       float(header_i['Image 000 [Spectroscopy images ramp value list]'].split(' ')[0])]
                        res_i = header_i['Number of rows [General Info]'] + 'x' + header_i['Number of columns [General Info]'] + 'x' + header_i['Number of points per ramp [General Info]']
                        size_i = header_i['X Amplitude [Control]'] + ' x ' + header_i['Y Amplitude [Control]'] + ' x ' + f'{int(max(z_extrema_i))}' + ' ' + header_i['Image 000 [Spectroscopy images ramp value list]'].split(' ')[1]
                        # xx_i, yy_i, zz_i = get_imgdata(data_dict_chan_i)
                        # plt.pcolormesh(xx_i, yy_i, zz_i, cmap='afmhot')
                        # plt.axis('off')
                        # fig_i = fig2html(plt.gcf(), plot_type='matplotlib')
                        # plt.close()
                        z_max_i = data_dict_chan_i['data']['Z'].max()
                        z_min_i = data_dict_chan_i['data']['Z'].min()
                        z_avg_i = data_dict_chan_i['data']['Z'].mean()
                        if flatten_chan == 'all' or 'Topography' in flatten_chan: #channel_i == 'Topography': #only flatten topography images
                            z_data_i = tsf.flatten_line(data_dict_chan_i['data'], order=1)
                        else:
                            z_data_i = data_dict_chan_i['data']['Z']
                        # z_data_i = tsf.flatten_line(data_dict_chan_i['data'], order=1) #flatten topography
                        if make_plot == True:
                            fig_i = fig2html(plotly_heatmap(x=data_dict_chan_i['data']['X'],
                                                            y=data_dict_chan_i['data']['Y'],
                                                            z_mat=z_data_i, style='clean'), 
                                             plot_type='plotly')
                        else:
                            fig_i = ''
                    elif path_ext_i in ['.curves', '.stp', '.cur']:
                        data_type_i = '1D'
                        # channel_i = filename_i[match_i.start()+6:].split('.')[0].split('_')[0]
                        # feedback_i = ''
                        data_dict_chan_i = wsxm_readspectra(path_i, all_files=False, mute=True)
                        header_i = data_dict_chan_i['header']
                        channel_i = header_i['Spectroscopy channel']
                        spec_dir_i = list(data_dict_chan_i['data'].keys())
                        
                        if path_ext_i == '.stp':                            
                            res_i = header_i['Number of columns [General Info]']
                            size_i = header_i['X Amplitude [Control]']
                        else: #for *.curves and *.cur
                            res_i = header_i['Number of points [General Info]']
                            size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit [General Info]']
                        spectrodf_i = convert_spectro2df(data_dict_chan_i['data'])
                        # sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
                        # fig_i = fig2html(plt.gcf())
                        z_avg_i = spectrodf_i.groupby(['segment']).mean()['y'].to_dict()
                        z_min_i = spectrodf_i.groupby(['segment']).min()['y'].to_dict()
                        z_max_i = spectrodf_i.groupby(['segment']).max()['y'].to_dict()
                        # z_max_i = spectrodf_i['y'].max()
                        # z_min_i = spectrodf_i['y'].min()
                        # z_avg_i = spectrodf_i['y'].mean()
                        if make_plot == True:
                            # g_i = plt.plot(spectrodf_i['x'], spectrodf_i['y']) #sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
                            # fig_i = fig2html(plt.gcf(), plot_type='matplotlib')
                            g_i = sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
                            fig_i = fig2html(g_i.figure, plot_type='matplotlib')
                            plt.clf()
                            # fig_i = fig2html(plotly_lineplot(data=spectrodf_i, x="x", y="y", color="segment"), plot_type='plotly')
                        else:
                            fig_i = ''
                        # plt.close()
                    else:
                        data_type_i = '2D'
                        # channel_i = WSXM_CHANNEL_DICT[path_ext_i[1:]]
                        file_tags_i = filename_i[match_i.start()+6:].split('.')
                        
                        data_dict_chan_i = wsxm_readchan(path_i, all_files=False, mute=True)
                        header_i = data_dict_chan_i['header']
                        channel_i = header_i['Acquisition channel [General Info]']
                        res_i = header_i['Number of rows [General Info]'] + 'x' + header_i['Number of columns [General Info]']
                        size_i = header_i['X Amplitude [Control]'] + ' x ' + header_i['Y Amplitude [Control]']
                        # feedback_i = header_i['Input channel']
                        # xx_i, yy_i, zz_i = get_imgdata(data_dict_chan_i)
                        # plt.pcolormesh(xx_i, yy_i, zz_i, cmap='afmhot')
                        
                        # plt.axis('off')
                        z_max_i = data_dict_chan_i['data']['Z'].max()
                        z_min_i = data_dict_chan_i['data']['Z'].min()
                        z_avg_i = data_dict_chan_i['data']['Z'].mean()
                        if flatten_chan == 'all' or channel_i in flatten_chan: #channel_i == 'Topography': #only flatten topography images
                            z_data_i = tsf.flatten_line(data_dict_chan_i['data'], order=1)
                        else:
                            z_data_i = data_dict_chan_i['data']['Z']
                        if make_plot == True:
                            fig_i = fig2html(plotly_heatmap(x=data_dict_chan_i['data']['X'],
                                                            y=data_dict_chan_i['data']['Y'],
                                                            z_mat=z_data_i, style='clean'), 
                                             plot_type='plotly')
                        else:
                            fig_i = ''
                        
                        # plt.close()
                else: #if no match for 4 digit counter found in file name
                    if path_ext_i == '.cur': #read other *.cur file e.g. tuning
                        filename_com_i = filename_i[:-4]
                        data_type_i = '1D'
                        # channel_i = 'Other'
                        data_dict_chan_i = wsxm_readspectra(path_i, all_files=False)
                        header_i = data_dict_chan_i['header']
                        channel_i = header_i['Spectroscopy channel']                        
                        res_i = header_i['Number of points [General Info]']
                        spec_dir_i = list(data_dict_chan_i['data'].keys())
                        size_i = str(data_dict_chan_i['data'][spec_dir_i[0]]['x'].max())  + ' ' + header_i['X axis unit [General Info]']
                        # feedback_i = ''
                        spectrodf_i = convert_spectro2df(data_dict_chan_i['data'])
                        #calculate statistics for each segment data 
                        z_avg_i = spectrodf_i.groupby(['segment']).mean()['y'].to_dict()
                        z_min_i = spectrodf_i.groupby(['segment']).min()['y'].to_dict()
                        z_max_i = spectrodf_i.groupby(['segment']).max()['y'].to_dict()
                        # z_max_i = spectrodf_i['y'].max()
                        # z_min_i = spectrodf_i['y'].min()
                        # z_avg_i = spectrodf_i['y'].mean()
                        if make_plot == True:
                            g_i = sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
                            fig_i = fig2html(g_i.figure, plot_type='matplotlib')
                            plt.clf()
                            # fig_i = fig2html(plotly_lineplot(data=spectrodf_i, x="x", y="y", color="segment"), plot_type='plotly')
                        else:
                            fig_i = ''
                        # sns.lineplot(data=spectrodf_i, x="x", y="y", hue="segment")
                        # fig_i = fig2html(plt.gcf())
                        # plt.close()
                # print(filename_i)
                file_dict['file'].append(filename_com_i)
                file_dict['name'].append(filename_i)
                file_dict['channel'].append(channel_i)
                file_dict['type'].append(data_type_i)
                file_dict['size'].append(size_i)
                file_dict['resolution'].append(res_i)
                file_dict['max'].append(str(z_max_i))
                file_dict['min'].append(str(z_min_i))
                file_dict['avg'].append(str(z_avg_i))
                # file_dict['feedback'].append(feedback_i)
                file_dict['plot'].append(fig_i)
                file_dict['extension'].append(path_ext_i)
                file_dict['time'].append(time_i)
                file_dict['header'].append(header_i)       
                file_dict['header names'].append(list(header_i.keys()))                         
        
        file_df = pd.DataFrame.from_dict(file_dict)
        # print(file_df['header names'].to_numpy().flatten().unique())   
        
        # file_df.drop(columns=['plot', 'header names']).to_excel(f"{folderpath}/filelist_{os.path.basename(folderpath)}.xlsx")
        file_df['header data'] = file_df['header'].map(str) #convert dictionary column data to string for excel saving
        file_df.sort_values(by=['time'], inplace=True, ignore_index=True)
        if make_plot == True:
            #save excel file for manual check including images
            # imagedf_to_excel(file_df.drop(columns=['header', 'header names']), 
            #                  f"{folderpath}/filelist_{os.path.basename(folderpath)}.xlsx", img_size=(100, 100))
            imagedf_to_excel(file_df.drop(columns=['header', 'header names']), 
                             folderpath / f"filelist_{folderpath.name}.xlsx", img_size=(100, 100))
        else:
            # file_df.to_excel(f"{folderpath}/filelist_{os.path.basename(folderpath)}.xlsx")
            file_df.to_excel(folderpath / f"filelist_{folderpath.name}.xlsx")
        file_df.drop(columns=['header data'], inplace=True) #remove "stringed" header data
        #save "pickled" binary data of file list for later use   
        # file_df.to_pickle(f"{folderpath}/filelist_{os.path.basename(folderpath)}.pkl")
        file_df.to_pickle(folderpath / f"filelist_{folderpath.name}.pkl")
    
    return file_df