# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 15:39:00 2020

@author: Rama Vasudevan

Modified: Ganesh Narasimha, 30 Sep 2026
"""

import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
from .nanonis_base import _split_channel_name, _unique_key, _sweep_ramps


class NanonisDatReader(Reader):
    """
    Reads files obtained via Nanonis controllers in .dat files.
    These are generally point spectroscopy measurements.

    """

    def read(self, verbose=False):
        """
        Reads the file given in file_path into sidpy datasets

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging

        Returns
        -------
        dict of sidpy.Dataset objects, one per data column, keyed by the column
        name as in the file without the unit ('Current', 'Current [bwd]').
        Column 0 (the swept signal, e.g. 'Bias calc (V)') is the spectral
        dimension of every dataset. Duplicate keys get a '_1', '_2', ... suffix.
        """

        file_path = self._input_file_path

        # Extracting the raw data into memory (Nanonis writes latin-1 text)
        with open(file_path, 'r', encoding='latin-1') as file_handle:
            string_lines = file_handle.read().splitlines()

        data_start = next((ind for ind, line in enumerate(string_lines)
                           if line.strip() == '[DATA]'), None)
        if data_start is None:
            raise ValueError('{} is not a Nanonis .dat file: no [DATA] section found'.format(file_path))
        header = string_lines[:data_start]

        column_names = [col for col in string_lines[data_start + 1].split('\t') if col.strip()]
        columns = [_split_channel_name(col) for col in column_names]

        # Extract parameters from the header lines
        parm_dict = self._read_parms(header)

        if verbose:
            print('Found parameters dictionary {}'.format(parm_dict))

        # Extract the STS data from subsequent lines
        raw_data = np.loadtxt(string_lines[data_start + 2:], ndmin=2)
        if verbose:
            print('Read data of shape {}'.format(raw_data.shape))

        # Generate the spectroscopic axis from column 0 (the swept signal)
        spec_vec = raw_data[:, 0]
        _, spec_name, _, spec_unit = columns[0]
        if verbose:
            print('Found spectroscopic vector of size {}'.format(spec_vec.shape))
            print('Spectroscopy vector has title {}'.format(spec_name))
            print('Spectroscopy vector values: {}'.format(spec_vec))

        # Forward and [bwd] columns share column 0 (stored in forward order);
        # in time, the forward sweep runs first -> last and [bwd] the other way.
        fwd_ramp, bwd_ramp = _sweep_ramps(spec_vec)

        dataset_dict = {}
        for chan_ind, (column_name, (key, name, direction, unit)) in enumerate(zip(column_names, columns)):
            if chan_ind == 0:  # 0th column is the spectral one
                continue
            key = _unique_key(key, dataset_dict)

            if verbose:
                print('Making sidpy dataset with channel {}'.format(key))

            # now write it to the sidpy dataset object
            data_set = sid.Dataset.from_array(raw_data[:, chan_ind], title=key)
            data_set.data_type = sid.DataType.SPECTRUM
            data_set.units = unit
            data_set.quantity = name

            # Add dimension info
            data_set.set_dimension(0, sid.Dimension(spec_vec, name=spec_name,
                                                    units=spec_unit, quantity=spec_name,
                                                    dimension_type=sid.DimensionType.SPECTRAL))

            # append metadata: per-channel keys + a copy of the file header
            chan_metadata = {'Name': name,
                             'Direction': direction,
                             'sweep_ramp': fwd_ramp if direction == 'forward' else bwd_ramp,
                             'Unit': unit,
                             'Channel': column_name.strip(),
                             }
            data_set.original_metadata = {**chan_metadata, **parm_dict}
            dataset_dict[key] = data_set

        # Return the sidpy datasets
        return dataset_dict

    @staticmethod
    def _read_parms(header):
        """
        Returns the parameters regarding the experiment as dictionary

        Parameters
        ----------
        header : list of strings
            Header lines of the data file (everything before [DATA])

        Returns
        -------
        parm_dict : dictionary
            Dictionary of parameters regarding the experiment. A single value
            is converted to float where possible; several values are kept as
            a list; an empty value is ''.
        """
        parm_dict = {}
        for line in header:
            vals = [val.strip() for val in line.rstrip('\r\n').split('\t')]
            key = vals[0]
            if not key:
                continue
            vals = [val for val in vals[1:] if val != '']
            if len(vals) == 0:
                val = ''
            elif len(vals) == 1:
                try:
                    #If the key, value pair is a float, convert it
                    val = float(vals[0])
                except ValueError:
                    val = vals[0]
            else:
                val = vals
            parm_dict[key] = val
        return parm_dict

    def can_read(self):
        """
        Tests whether or not the provided file has a .dat extension
        Returns
        -------
        bool
            True if the file has a .dat extension, False otherwise
        """

        return self._input_file_path.lower().endswith('.dat')
