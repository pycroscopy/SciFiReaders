# -*- coding: utf-8 -*-
"""
Created on Fri Nov 5 16:43:00 2021

@author: Rama Vasudevan
"""
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader, Dimension, DimensionType

try:
    import nanonispy as nap
except ModuleNotFoundError:
    nap = None

class NanonisSXMReader(Reader):

    def __init__(self, file_path, *args, **kwargs):
        if nap == None:
            raise ModuleNotFoundError('You attempted to load a Nanonis file, but this requires Nanonispy.\n \
            Please Load it with pip install nanonispy , restart and retry')
        super().__init__(file_path, *args, **kwargs)

    @staticmethod
    def _parse_sxm_parms(header_dict, signal_dict):
        """
        Parse sxm files.
        Parameters
        ----------
        header_dict : dict
        signal_dict : dict
        Returns
        -------
        parm_dict : dict
        """
        parm_dict = dict()
        data_dict = dict()

        # Create dictionary with measurement parameters
        meas_parms = {key: value for key, value in header_dict.items()
                      if value is not None}
        info_dict = meas_parms.pop('data_info')
        parm_dict['meas_parms'] = meas_parms

        # Create dictionary with channel parameters
        channel_parms = dict()
        channel_names = info_dict['Name']
        single_channel_parms = {name: dict() for name in channel_names}
        for field_name, field_value, in info_dict.items():
            for channel_name, value in zip(channel_names, field_value):
                single_channel_parms[channel_name][field_name] = value
        for value in single_channel_parms.values():
            if value['Direction'] == 'both':
                value['Direction'] = ['forward', 'backward']
            else:
                direction = [value['Direction']]
        scan_dir = meas_parms['scan_dir']
        for name, parms in single_channel_parms.items():
            for direction in parms['Direction']:
                key = ' '.join((name, direction))
                channel_parms[key] = dict(parms)
                channel_parms[key]['Direction'] = direction
                data = signal_dict[name][direction]
                if scan_dir == 'up':
                    data = np.flip(data, axis=0)
                if direction == 'backward':
                    data = np.flip(data, axis=1)
                data_dict[key] = data
        parm_dict['channel_parms'] = channel_parms

        # Position dimensions
        num_cols, num_rows = header_dict['scan_pixels']
        width, height = header_dict['scan_range']
        pos_names = ['X', 'Y']
        pos_units = ['nm', 'nm']
        pos_vals = np.vstack([
            np.linspace(0, width, num_cols),
            np.linspace(0, height, num_rows),
        ])
        pos_vals *= 1e9
        dims = [Dimension(values, name=name, quantity='Length', units=unit,
                          dimension_type=DimensionType.SPATIAL) for
                name, unit, values
                in zip(pos_names, pos_units, pos_vals)]
        data_dict['Dimensions'] = dims

        return parm_dict, data_dict

  
    def read(self):
        """
        Reads data from .sxm files into sidpy.Dataset objects
        Note that multiple channels are treated as separate dataset objects,
        Thus returning a list of length N where N is the number of channels.

        Returns
        -------
        dataset_list: (list) of sidpy.Dataset objects
        """
       
        reader = nap.read.Scan
       
        nanonis_data = reader(self._input_file_path)

        header_dict = nanonis_data.header
        signal_dict = nanonis_data.signals

        parm_dict, data_dict = self._parse_sxm_parms(header_dict,
                                                         signal_dict)
        
        self.parm_dict = parm_dict
        self.data_dict = data_dict

        #Specify dimensions
        x_dim = self.data_dict['Dimensions'][0]
        y_dim = self.data_dict['Dimensions'][1]

        dataset_list = []
        channel_parms = self.parm_dict['channel_parms']

        for dataset_name in list(self.data_dict.keys())[:-1]:
            
            data_mat = self.data_dict[dataset_name]
            
            #Make a sidpy dataset
            data_set = sid.Dataset.from_array(data_mat, name = dataset_name)

            #Set the data type
            data_set.data_type = sid.DataType.IMAGE
            
            metadata = channel_parms[dataset_name]

            # Add quantity and units
            data_set.units = metadata['Unit']
            data_set.quantity = metadata['Name']

            # Add dimension info
            data_set.set_dimension(0, x_dim)
            data_set.set_dimension(1, y_dim)
        
            # append metadata 
            def merge_dict(dict1, dict2):
                res = {**dict1, **dict2}
                return res
            
            chan_metadata = self.parm_dict['channel_parms'][dataset_name]
            orig_metadata = self.parm_dict['meas_parms']
            
            data_set.original_metadata =  merge_dict(chan_metadata,orig_metadata)
            dataset_list.append(data_set)
        
        return dataset_list

    def can_read(self):
        """
        Tests whether or not the provided file has a .dm3 extension
        Returns
        -------
        """
        # TODO: Add dat eventually
        if nap is None:
            return False
        return super(NanonisSXMReader, self).can_read(extension='sxm')