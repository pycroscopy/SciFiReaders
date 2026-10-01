# -*- coding: utf-8 -*-
"""
Created on Fri Nov 5 16:43:00 2021

@author: Rama Vasudevan

Modified: Ganesh Narasimha, 30 Sep 2026
"""

import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader, Dimension, DimensionType
from .nanonis_base import Grid, _as_list, _split_channel_name, _unique_key, _sweep_ramps

class Nanonis3dsReader(Reader):

    def __init__(self, file_path, *args, **kwargs):

        super().__init__(file_path, *args, **kwargs)

    @staticmethod
    def _split_channel_name(chan_name):
        """
        Split a Nanonis channel name such as 'LI Demod 1 X [bwd] (A)' into
        (name, direction, unit) -> ('LI Demod 1 X', 'backward', 'A').
        Backward sweeps are marked with '[bwd]'; everything else is forward.
        """
        _, name, direction, unit = _split_channel_name(chan_name)
        return name, direction, unit

    @staticmethod
    def _unique_key(key, existing):
        """
        Return key unchanged if unused, otherwise the first free 'key_1', 'key_2', ...
        (with a warning). The first occurrence keeps the original name.
        """
        return _unique_key(key, existing)

    @staticmethod
    def _collapse_param_grid(parm_grid):
        """Return a scalar if the (ny, nx) grid is constant, otherwise the full grid."""
        finite = parm_grid[np.isfinite(parm_grid)]
        if finite.size == 0:
            return parm_grid
        if np.all(finite == finite[0]):
            return finite[0]
        return parm_grid

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
        param_names = _as_list(meas_parms.pop('fixed_parameters')) \
            + _as_list(meas_parms.pop('experimental_parameters'))
        # params has shape (ny, nx, num_parameters): each parameter is a (ny, nx) grid
        for key, parm_grid in zip(param_names, np.moveaxis(signal_dict['params'], -1, 0)):
            meas_parms[key] = Nanonis3dsReader._collapse_param_grid(parm_grid)
        parm_dict['meas_parms'] = meas_parms

        # Create dictionary with channel parameters and
        # save channel data before renaming keys
        data_channel_parms = dict()
        channel_data = signal_dict.pop('channel_data')
        # Forward and [bwd] data are both stored against the same sweep axis
        # (Sweep Start -> Sweep End); in time, the forward sweep ramps from
        # Sweep Start to Sweep End and the [bwd] sweep the opposite way.
        fwd_ramp, bwd_ramp = _sweep_ramps(signal_dict['sweep_signal'])
        for chan_name, chan_data in zip(channels, channel_data):
            # key is the channel name as in the file, without the unit: 'Current', 'Current [bwd]'
            key, name, direction, unit = _split_channel_name(chan_name)
            key = _unique_key(key, data_channel_parms)
            data_channel_parms[key] = {'Name': name,
                                       'Direction': direction,
                                       'sweep_ramp': fwd_ramp if direction == 'forward' else bwd_ramp,
                                       'Unit': unit,
                                       'Channel': chan_name,
                                       }
            data_dict[key] = chan_data
            signal_dict.pop(chan_name, None)
        parm_dict['channel_parms'] = data_channel_parms

        # Add remaining signal_dict elements to data_dict
        data_dict.update(signal_dict)

        # Position dimensions. Data is stored as (ny, nx, points): axis 0 is
        # the slow (Y) direction, axis 1 the fast (X) direction. Values are
        # pixel positions in the (possibly rotated) grid frame, starting at 0.
        # The frame centre and angle are in the metadata ('pos_xy', 'angle'),
        # the true per-pixel positions in meas_parms['X (m)'] / ['Y (m)'].
        nx, ny = header_dict['dim_px']
        size_x, size_y = header_dict['size_xy']
        x_vals = np.arange(nx) * size_x / nx * 1e9
        y_vals = np.arange(ny) * size_y / ny * 1e9

        dims = [Dimension(y_vals, name='Y', quantity='Length', units='nm',
                          dimension_type=DimensionType.SPATIAL),
                Dimension(x_vals, name='X', quantity='Length', units='nm',
                          dimension_type=DimensionType.SPATIAL)]

        # Spectroscopic dimensions
        sweep_signal = header_dict['sweep_signal']
        spec_label, _, spec_unit = Nanonis3dsReader._split_channel_name(sweep_signal)
        dc_offset = data_dict['sweep_signal']
        spec_dim = Dimension(dc_offset, quantity=spec_label, name=spec_label,
                             units=spec_unit,
                             dimension_type=DimensionType.SPECTRAL)
        dims.append(spec_dim)
        data_dict['Dimensions'] = dims

        return parm_dict, data_dict

    def read(self):
        """
        Returns
        -------
        dict of sidpy.Dataset objects containing the spectroscopy data,
        keyed by channel name as in the file without the unit ('Current',
        'Current [bwd]'), plus a 'Topography' image (Z at each pixel) when
        the grid recorded 'Z (m)'. Duplicate keys get a '_1', '_2', ... suffix.
        """

        nanonis_data = Grid(self._input_file_path)

        header_dict = nanonis_data.header
        signal_dict = nanonis_data.signals

        parm_dict, data_dict = self._parse_3ds_parms(header_dict,
                                                     signal_dict)

        self.parm_dict = parm_dict
        self.data_dict = data_dict

        #Specify dimensions
        y_dim, x_dim, spec_dim = self.data_dict['Dimensions']

        dataset_dict = {}
        channel_parms = self.parm_dict['channel_parms']
        orig_metadata = self.parm_dict['meas_parms']

        for dataset_name, chan_metadata in channel_parms.items():

            data_mat = self.data_dict[dataset_name]

            #Make a sidpy dataset
            data_set = sid.Dataset.from_array(data_mat, title=dataset_name)

            #Set the data type
            data_set.data_type = sid.DataType.SPECTRAL_IMAGE

            # Add quantity and units
            data_set.units = chan_metadata['Unit']
            data_set.quantity = chan_metadata['Name']

            # Add dimension info
            data_set.set_dimension(0, y_dim)
            data_set.set_dimension(1, x_dim)
            data_set.set_dimension(2, spec_dim)

            # append metadata
            data_set.original_metadata = {**chan_metadata, **orig_metadata}
            dataset_dict[dataset_name] = data_set

        topo = self.data_dict.get('topo')
        if topo is not None:
            topo_key = self._unique_key('Topography', dataset_dict)
            data_set = sid.Dataset.from_array(topo, title=topo_key)
            data_set.data_type = sid.DataType.IMAGE
            data_set.units = 'm'
            data_set.quantity = 'Z'
            data_set.set_dimension(0, y_dim.copy())
            data_set.set_dimension(1, x_dim.copy())
            data_set.original_metadata = {'Name': 'Z', 'Unit': 'm', 'Channel': 'Z (m)', **orig_metadata}
            dataset_dict[topo_key] = data_set

        return dataset_dict


    def can_read(self):
        """
        Tests whether or not the provided file has a .3ds extension
        Returns
        -------
        bool
            True if the file has a .3ds extension, False otherwise
        """

        return self._input_file_path.lower().endswith('.3ds')