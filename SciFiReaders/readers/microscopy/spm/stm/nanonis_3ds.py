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


class Nanonis3dsReader(Reader):

    def __init__(self, file_path, *args, **kwargs):
        if nap == None:
            raise ModuleNotFoundError('You attempted to load a Nanonis file, but this requires Nanonispy.\n \
            Please Load it with pip install nanonispy , restart and retry')
        super().__init__(file_path, *args, **kwargs)

    @staticmethod
    def _parse_3ds_parms(header_dict, signal_dict):
        """
        Parse 3ds files.
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
        channels = meas_parms.pop('channels')
        for key, parm_grid in zip(meas_parms.pop('fixed_parameters')
                                  + meas_parms.pop('experimental_parameters'),
                                  signal_dict['params'].T):
            # Collapse the parm_grid along one axis if it's constant
            # along said axis
            if parm_grid.ndim > 1:
                dim_slice = list()
                # Find dimensions that are constant
                for idim in range(parm_grid.ndim):
                    tmp_grid = np.moveaxis(parm_grid.copy(), idim, 0)
                    if np.all(np.equal(tmp_grid[0], tmp_grid[1])):
                        dim_slice.append(0)
                    else:
                        dim_slice.append(slice(None))
                # print(key, dim_slice)
                # print(parm_grid[tuple(dim_slice)])
                parm_grid = parm_grid[tuple(dim_slice)]
            meas_parms[key] = parm_grid
        parm_dict['meas_parms'] = meas_parms

        # Create dictionary with channel parameters and
        # save channel data before renaming keys
        data_channel_parms = dict()
        for chan_name in channels:
            splitted_chan_name = chan_name.split(maxsplit=2)
            if len(splitted_chan_name) == 2:
                direction = 'forward'
            elif len(splitted_chan_name) == 3:
                direction = 'backward'
                splitted_chan_name.pop(1)
            name, unit = splitted_chan_name
            key = ' '.join((name, direction))
            data_channel_parms[key] = {'Name': name,
                                       'Direction': direction,
                                       'Unit': unit.strip('()'),
                                       }
            data_dict[key] = signal_dict.pop(chan_name)
        parm_dict['channel_parms'] = data_channel_parms

        # Add remaining signal_dict elements to data_dict
        data_dict.update(signal_dict)

        # Position dimensions
        nx, ny = header_dict['dim_px']
        if 'X (m)' in parm_dict:
            row_vals = parm_dict.pop('X (m)')
        else:
            row_vals = np.arange(nx, dtype=np.float32)

        if 'Y (m)' in parm_dict:
            col_vals = parm_dict.pop('Y (m)')
        else:
            col_vals = np.arange(ny, dtype=np.float32)
        pos_vals = np.hstack([row_vals.reshape(-1, 1),
                              col_vals.reshape(-1, 1)])
        pos_names = ['X', 'Y']

        dims = [Dimension(values, name=label, quantity='Length', units='nm',
                          dimension_type=DimensionType.SPATIAL)
                for label, values in zip(pos_names, pos_vals.T)]

        # Spectroscopic dimensions
        sweep_signal = header_dict['sweep_signal']
        spec_label, spec_unit = sweep_signal.split(maxsplit=1)
        spec_unit = spec_unit.strip('()')
        # parm_dict['sweep_signal'] = (sweep_name, sweep_unit)
        dc_offset = data_dict['sweep_signal']
        spec_dim = Dimension(dc_offset, quantity='Bias', name=spec_label,
                             units=spec_unit,
                             dimension_type=DimensionType.SPECTRAL)
        dims.append(spec_dim)
        data_dict['Dimensions'] = dims

        return parm_dict, data_dict

    def read(self):
        """
        Returns
        -------
        list of sidpy.Dataset objects containing the spectroscopy data
        """
        
        reader = nap.read.Grid
        override_header = {
            'Delay before measuring (s)': 0.0,
            'Start time': 0.0,
            'End time': 1000.0,
            'Comment': 'Default values for delay before measuring (s), Start time and End time fields were used! Beware!'
        }
        nanonis_data = reader(self._input_file_path, header_override=override_header)

        header_dict = nanonis_data.header
        signal_dict = nanonis_data.signals

        parm_dict, data_dict = self._parse_3ds_parms(header_dict,
                                                         signal_dict)
      
        self.parm_dict = parm_dict
        self.data_dict = data_dict

        #Specify dimensions
        x_dim = self.data_dict['Dimensions'][0]
        y_dim = self.data_dict['Dimensions'][1]
        z_dim = self.data_dict['Dimensions'][2]

        dataset_list = []
        channel_parms = self.parm_dict['channel_parms']
        orig_metadata = self.parm_dict['meas_parms']

        chan_names = list(self.parm_dict['channel_parms'].keys())

        for dataset_name in chan_names:
            
            data_mat = self.data_dict[dataset_name]
            
            #Make a sidpy dataset
            data_set = sid.Dataset.from_array(data_mat, name = dataset_name)

            #Set the data type
            data_set.data_type = sid.DataType.SPECTRAL_IMAGE
            
            metadata = channel_parms[dataset_name]

            # Add quantity and units
            data_set.units = metadata['Unit']
            data_set.quantity = metadata['Name']

            # Add dimension info
            data_set.set_dimension(0, x_dim)
            data_set.set_dimension(1, y_dim)
            data_set.set_dimension(2, z_dim)
        
            # append metadata 
            def merge_dict(dict1, dict2):
                res = {**dict1, **dict2}
                return res
            
            chan_metadata = self.parm_dict['channel_parms'][dataset_name]
            
            data_set.original_metadata =  merge_dict(chan_metadata,orig_metadata)
            dataset_list.append(data_set)
        
        return dataset_list
        
        return 

    def can_read(self):
        """
        Tests whether or not the provided file has a .3ds extension
        Returns
        -------
        """
    
        if nap is None:
            return False
        return super(Nanonis3dsReader, self).can_read(extension='3ds')