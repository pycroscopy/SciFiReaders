# -*- coding: utf-8 -*-
"""
Created on Fri Nov 5 16:43:00 2021

@author: Rama Vasudevan

Modified: Ganesh Narasimha, 30 Sep 2026
"""
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader, Dimension, DimensionType
from .nanonis_base import Scan, _sxm_directions

class NanonisSXMReader(Reader):

    def __init__(self, file_path, *args, **kwargs):
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
                if field_name in ('Calibration', 'Offset'):
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                single_channel_parms[channel_name][field_name] = value
        scan_dir = meas_parms['scan_dir']
        for name, parms in single_channel_parms.items():
            # 'both' -> one dataset per direction; a single-direction channel -> one dataset
            for direction in _sxm_directions(parms['Direction']):
                key = ' '.join((name, direction))
                channel_parms[key] = dict(parms)
                channel_parms[key]['Direction'] = direction
                data = signal_dict[name][direction]
                if scan_dir == 'down':                 # Flip the data vertically if the scan direction is down
                    data = np.flip(data, axis=0)
                if direction == 'backward':
                    data = np.flip(data, axis=1)
                data_dict[key] = data
        parm_dict['channel_parms'] = channel_parms

        # Position dimensions. Images are (rows, cols) = (ny, nx): axis 0 is Y,
        # axis 1 is X. After the flips above, row 0 is the bottom and column 0
        # the left of the scan frame. Values are pixel positions in the (possibly
        # rotated) frame starting at 0 with pitch range / pixels, as for .3ds;
        # offset and angle are in the metadata ('scan_offset', 'scan_angle').
        num_cols, num_rows = header_dict['scan_pixels']
        width, height = header_dict['scan_range']
        x_vals = np.arange(num_cols) * width / num_cols * 1e9
        y_vals = np.arange(num_rows) * height / num_rows * 1e9
        dims = [Dimension(y_vals, name='Y', quantity='Length', units='nm',
                          dimension_type=DimensionType.SPATIAL),
                Dimension(x_vals, name='X', quantity='Length', units='nm',
                          dimension_type=DimensionType.SPATIAL)]
        data_dict['Dimensions'] = dims

        return parm_dict, data_dict

  
    def read(self):
        """
        Reads data from .sxm files into sidpy.Dataset objects.
        Each channel and recorded direction is a separate dataset.

        Returns
        -------
        dataset_dict: dict of sidpy.Dataset objects keyed '<name> forward' /
        '<name> backward'. Images are (ny, nx) with row 0 at the bottom and
        column 0 at the left of the scan frame (plot with origin='lower').
        """
       
        reader = Scan
       
        nanonis_data = reader(self._input_file_path)

        header_dict = nanonis_data.header
        signal_dict = nanonis_data.signals

        parm_dict, data_dict = self._parse_sxm_parms(header_dict,
                                                         signal_dict)
        
        self.parm_dict = parm_dict
        self.data_dict = data_dict

        #Specify dimensions
        y_dim, x_dim = self.data_dict['Dimensions']

        dataset_dict = {}
        channel_parms = self.parm_dict['channel_parms']

        for dataset_name in channel_parms:
            
            data_mat = self.data_dict[dataset_name]
            
            #Make a sidpy dataset
            data_set = sid.Dataset.from_array(data_mat, title=dataset_name)

            #Set the data type
            data_set.data_type = sid.DataType.IMAGE
            
            metadata = channel_parms[dataset_name]

            # Add quantity and units
            data_set.units = metadata['Unit']
            data_set.quantity = metadata['Name']

            # Add dimension info
            data_set.set_dimension(0, y_dim)
            data_set.set_dimension(1, x_dim)
        
            # append metadata 
            def merge_dict(dict1, dict2):
                res = {**dict1, **dict2}
                return res
            
            chan_metadata = self.parm_dict['channel_parms'][dataset_name]
            orig_metadata = self.parm_dict['meas_parms']
            
            data_set.original_metadata =  merge_dict(chan_metadata,orig_metadata)
            dataset_dict[dataset_name] = data_set
        
        return dataset_dict

    def can_read(self):
        """
        Tests whether or not the provided file has a .sxm extension
        Returns
        -------
        bool
            True if the file has a .sxm extension, False otherwise
        """
       
        return self._input_file_path.lower().endswith('.sxm')