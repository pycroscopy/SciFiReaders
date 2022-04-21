# -*- coding: utf-8 -*-
"""
Created on Fri Dec 10 15:48:00 2021

@author: Rama Vasudevan, based on a translator in legacy pycroscopy
which was created on Fri May 25 16:04:34 2016 by  Suhas Somnath

"""

from os import stat
import sys
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
from .base_utils import read_binary_data

from collections import OrderedDict

class BrukerAFMReader(Reader):
    """
    Extracts data and metadata from Bruker AFM (.nnn) files containing
    images or force curves where n is an integer

    """

    def read(self, verbose=False, parm_encoding='utf-8'):
        """
        Reads the file given in file_path into a sidpy dataset

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging
        parm_encoding : str, optional
            Codec to be used to decode the bytestrings into Python strings if
            needed. Default 'utf-8'

        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Multi-channel inputs are separated into individual sidpy dataset objects
        """
        self.file_path = self._input_file_path
        self.meta_data, other_parms = self._extract_metadata()

        type_suffixes = ['Image', 'Force_Curve', 'Force_Map']
        # 0 - stack of scan images
        # 1 - single force curve
        # 2 - force map
        force_count = 0
        image_count = 0
        for class_name in self.meta_data.keys():
            if 'Ciao force image list' in class_name:
                force_count += 1
            elif 'Ciao image list' in class_name:
                image_count += 1
        data_type = 0
        if force_count > 0:
            if image_count > 0:
                data_type = 2
            else:
                data_type = 1

        global_parms = dict()
        global_parms['data_type'] = 'Bruker_AFM_' + type_suffixes[data_type]
        global_parms['translator'] = 'Bruker_AFM'

        flat_dict = dict()
        for class_name, sub_dict in other_parms.items():
            for key, val in sub_dict.items():
                flat_dict[class_name + '_' + key] = val

        trans_funcs = [self._read_image_stack, self._read_force_curve, self._read_force_map]
        dataset = trans_funcs[data_type]()

        return dataset

    def _read_force_curve(self):
        """
        Reads the force curves from the proprietary file and writes them to sidpy dataset object
        
        """
       
        # Find out the size of the force curves from the metadata:
        layer_info = None
        for class_name in self.meta_data.keys():
            if 'Ciao force image list' in class_name:
                layer_info = self.meta_data[class_name]
                break
        
        tr_rt = [int(item) for item in layer_info['Samps/line'].split(' ')]
        m=0
        datasets = []
        titles = []
        metadata = []
        for class_name in self.meta_data.keys():
            if 'Ciao force image list' in class_name:
                layer_info = self.meta_data[class_name]
                quantity = layer_info.pop('Image Data_4')
                title = quantity.split("\"")[1]
                data = self._read_data_vector(layer_info)
                self.data = data
                data_split =  np.split(data, len(data)//tr_rt[m])
                titles.append((title, quantity))
                datasets.append(data_split)
                metadata.append(layer_info)
                m+=1

        xdata = datasets[1] #not sure if this is right but let's go with it.
        title = titles[0][0]
        quantity = titles[0][1]
        
        sid_datasets = []

        for k in range(len(datasets[0])):
            zdata = datasets[0][k]
            xdata = datasets[1][k]
            
            data_set = sid.Dataset.from_array(zdata, name=title)
            data_set.data_type = 'Spectrum'

            #Add quantity and units
            data_set.units = 'nm' #check this one
            data_set.quantity = quantity

            #Add dimension info
            data_set.set_dimension(0, sid.Dimension(xdata,
                                                    name = 'z',
                                                    units='nm', quantity = 'z',
                                                    dimension_type='spectral'))
            
            data_set.original_metadata = metadata[k]
            sid_datasets.append(data_set)

        return sid_datasets

    def _read_image_stack(self):
        """
        Reads the scan images from the proprietary file and puts them into sidpy.Dataset
        Parameters
        ----------

        """
      
        # Find out the size of the force curves from the metadata:
        layer_info = None
        for class_name in self.meta_data.keys():
            if 'Ciao image list' in class_name:
                layer_info = self.meta_data[class_name]
                break
        
        #Here are teh dimension details
        num_samps_line = layer_info['Samps/line']
        num_lines = layer_info['Number of lines']
       
        #Read through and write to sidpy dataset objects
        datasets = []
        for class_name in self.meta_data.keys():
            if 'Ciao image list' in class_name:
                layer_info = self.meta_data[class_name]
                #print(layer_info)
                quantity = layer_info.pop('Image Data_2')
                title = quantity.split("\"")[1]
                data = self._read_image_layer(layer_info)
                num_cols, num_rows = data.shape
                data_set = sid.Dataset.from_array(data, name=title)
                data_set.data_type = 'Image'

                #Add quantity and units
                data_set.units = 'nm' #check this one
                data_set.quantity = quantity

                #Add dimension info
                data_set.set_dimension(0, sid.Dimension(np.linspace(0, num_samps_line, num_cols),
                                                        name = 'x',
                                                        units='nm', quantity = 'x',
                                                        dimension_type='spatial'))
                data_set.set_dimension(1, sid.Dimension(np.linspace(0, num_lines, num_rows),
                                                        name = 'y',
                                                        units='nm', quantity='y',
                                                        dimension_type='spatial'))

                # append metadata
                data_set.original_metadata = self.meta_data[class_name]
                data_set.data_type = 'image'

                datasets.append(data_set)

        return datasets
        

    def _read_force_map(self):
        """
        Reads the scan image + force map from the proprietary file and writes it to sidpy datasets
        Parameters
        ----------
        h5_meas_grp : h5py.Group object
            Reference to the measurement group
        """
        # First lets write the image into the measurement group that has already been created:
        image_parms = self.meta_data['Ciao image list']
        quantity = image_parms.pop('Image Data_2')
        image_mat = self._read_image_layer(image_parms)
        #h5_chan_grp = create_indexed_group(h5_meas_grp, 'Channel')
        #write_main_dataset(h5_chan_grp, np.reshape(image_mat, (-1, 1)), 'Raw_Data',
        #                   # Quantity and Units needs to be fixed by someone who understands these files better
        #                   quantity, 'a. u.',
        #                   [Dimension('X', 'nm', image_parms['Samps/line']),
        #                    Dimension('Y', 'nm', image_parms['Number of lines'])],
        #                   Dimension('single', 'a. u.', 1), dtype=np.float32, compression='gzip')
        # Think about standardizing attributes for rows and columns
        #write_simple_attrs(h5_chan_grp, image_parms)

        # Now work on the force map:
        force_map_parms = self.meta_data['Ciao force image list']
        quantity = force_map_parms.pop('Image Data_4')
        force_map_vec = self._read_data_vector(force_map_parms)
        tr_rt = [int(item) for item in force_map_parms['Samps/line'].split(' ')]
        force_map_2d = force_map_vec.reshape(image_mat.size, np.sum(tr_rt))
        #h5_chan_grp = create_indexed_group(h5_meas_grp, 'Channel')
        #write_main_dataset(h5_chan_grp, force_map_2d, 'Raw_Data',
        #                   # Quantity and Units needs to be fixed by someone who understands these files better
        #                   quantity, 'a. u.',
        #                   [Dimension('X', 'nm', image_parms['Samps/line']),
        #                    Dimension('Y', 'nm', image_parms['Number of lines'])],
        #                   Dimension('Z', 'nm', int(np.sum(tr_rt))), dtype=np.float32, compression='gzip')
        # Think about standardizing attributes
        #write_simple_attrs(h5_chan_grp, force_map_parms)

        return force_map_2d

    def _extract_metadata(self):
        """
        Reads the metadata in the header
        Returns
        -------
        meas_parms : OrderedDict
            Ordered dictionary of Ordered dictionaries (one per image / force channel, etc.)
        other_parms : OrderedDict
            Ordered Dictionary of Ordered dictionaries containing all other metadata
        """
        other_parms = OrderedDict()
        meas_parms = OrderedDict()
        curr_category = ''
        temp_dict = OrderedDict()
        with open(self.file_path, "rb") as file_handle:
            for ind, line in enumerate(file_handle):
                line = line.decode("utf-8", 'ignore')
                trimmed = line.strip().replace("\\", "").replace('@', '')
                split_data = trimmed.split(':')

                # First account for wierdly formatted metadata that
                if len(split_data) == 3:
                    split_data = [split_data[1] + '_' + split_data[0], split_data[-1]]
                elif len(split_data) > 3:
                    # Date:
                    split_ind = trimmed.index(':')
                    split_data = [trimmed[:split_ind], trimmed[split_ind + 1:]]

                # At this point, split_data should only contain either 1 (class header) or 2 elements
                if len(split_data) == 1:
                    if len(temp_dict) > 0:
                        if 'Ciao image list' in curr_category or 'Ciao force image list' in curr_category:
                            # In certain cases the same class name occurs multiple times.
                            # Append suffix to existing name and to this name
                            count = 0
                            for class_name in meas_parms.keys():
                                if curr_category in class_name:
                                    count += 1
                            if count == 0:
                                meas_parms[curr_category] = temp_dict.copy()
                            else:
                                if count == 1:
                                    for class_name in meas_parms.keys():
                                        if curr_category == class_name:
                                            # Remove and add back again with suffix
                                            # This should only ever happen once.
                                            # The next time we come across the same class, all elements already have
                                            # suffixes
                                            meas_parms[curr_category + '_0'] = meas_parms.pop(curr_category)
                                            break
                                meas_parms[curr_category + '_' + str(count)] = temp_dict.copy()
                        else:
                            curr_category = curr_category.replace('Ciao ', '')
                            other_parms[curr_category] = temp_dict.copy()

                    if "*File list end" in trimmed:
                        break
                    curr_category = split_data[0].replace('*', '')
                    temp_dict = OrderedDict()
                elif len(split_data) == 2:
                    split_data = [item.strip() for item in split_data]
                    try:
                        num_val = float(split_data[1])
                        if int(num_val) == num_val:
                            num_val = int(num_val)
                        temp_dict[split_data[0]] = num_val
                    except ValueError:
                        temp_dict[split_data[0]] = split_data[1]
                else:
                    print(split_data)

        return meas_parms, other_parms

    def _read_data_vector(self, layer_info):
        """
        Reads data relevant to a single image, force curve, or force map
        Parameters
        ----------
        layer_info : OrderedDictionary
            Parameters describing the data offset, length and precision in the binary file
        Returns
        -------
        data_vec : np.ndarray
            1D array containing data represented by binary data
        """
        data_vec = read_binary_data(self.file_path, layer_info['Data offset'], layer_info['Data length'],
                                    layer_info['Bytes/pixel'])

        # Remove translation specific values from dictionary:
        for key in ['Data offset', 'Data length', 'Bytes/pixel']:
            _ = layer_info.pop(key)
        return data_vec
    
    def _read_image_layer(self, layer_info):
        """
        Reads a single scan image layer / channel
        Parameters
        ----------
        layer_info : OrderedDictionary
            Parameters describing the data offset, length and precision in the binary file
        Returns
        -------
        data_mat : numpy.ndarray
            2D array representing the requested channel of information
        """
        data_vec = self._read_data_vector(layer_info)
        data_mat = data_vec.reshape(layer_info['Number of lines'], layer_info['Samps/line'])
        return data_mat
    
    def can_read(self):
        """
        Tests whether or not the provided file has a suitable extension
        Returns
        -------
        not used for now...
        
        """
        return super(BrukerAFMReader, self).can_read(extension='')

