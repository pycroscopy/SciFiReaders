# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 15:39:00 202`0`

@author: Rama Vasudevan
"""

import sys
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
import re
from os import path


class NanonisDatReader(Reader):
    """
    Reads files obtained via Nanonis controllers in .dat files.
    These are generally point spectroscopy measurements.

    """

    def read(self, verbose=False):
        """
        Reads the file given in file_path into a sidpy dataset

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging

        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Multi-channel inputs are separated into individual dataset objects
        """

        file_path = self._input_file_path
        folder_path, file_name = path.split(file_path)

        # Extracting the raw data into memory
        file_handle = open(file_path, 'r')
        string_lines = file_handle.readlines()
        file_handle.close()

        data_start = string_lines.index('[DATA]\n')
        header = string_lines[:data_start - 1]

        channel_names_with_units = string_lines[data_start+1].split('\t')
        channel_names = [channel_names_with_units[ind].split('(')[0] for ind in range (len(channel_names_with_units))]
        channel_units = [re.search(r'\((.*?)\)',channel_names_with_units[ind]).group(1) for ind in range (len(channel_names_with_units))]

        # Extract parameters from the first few header lines
        parm_dict = self._read_parms(header)

        if verbose:
            print('Found parameters dictionary {}'.format(parm_dict))

        # Extract the STS data from subsequent lines
        raw_data = np.loadtxt(file_path, skiprows=data_start+2)
        if verbose:
            print('Read data of shape {}'.format(raw_data.shape))

        # Generate the x / voltage ß/ spectroscopic axis:
        volt_vec = raw_data[:,0]
        if verbose:
            print('Found spectroscopic vector of size {}'.format(volt_vec.shape))
            print('Spectroscopy vector has title {}'.format(channel_names[0]))
            print('Spectrsocopy vector values: {}'.format(volt_vec))
        datasets = [] #list of sidpy datasets that will be output

        # Add quantity and units
        for chan_ind, chan_name in enumerate(channel_names[1:]): #start from 1 because 0th column is the spectral one

            if verbose:
                print('Making sidpy dataset with channel {}'.format(chan_name))

            # now write it to the sidpy dataset object
            data_set = sid.Dataset.from_array(raw_data[:,chan_ind+1], name=chan_name)
            data_set.data_type = 'spectrum'
            data_set.units = channel_units[chan_ind+1]
            data_set.quantity = chan_name

            # Add dimension info
            data_set.set_dimension(0, sid.Dimension(volt_vec, name=chan_name,
                                                    units=channel_units[0], quantity='Voltage',
                                                    dimension_type=sid.DimensionType.SPECTRAL))

            # append metadata
            data_set.original_metadata = parm_dict
            datasets.append(data_set)

        # Return the sidy dataset
        return datasets

    @staticmethod
    def _read_parms(header):
        """
        Returns the parameters regarding the experiment as dictionary

        Parameters
        ----------
        string_lines : list of strings
            Lines from the data file in string representation

        Returns
        -------
        parm_dict : dictionary
            Dictionary of parameters regarding the experiment
        """
        # Reading parameters stored in the first few rows of the file
        # "Look through the header and create a dictionary from it"
        parm_dict = {}
        for line in header:
            vals = line.split('\t')
            key = vals[0]
            if len(vals[1:-1]) == 1:
                try:
                    #If the key, value pair is a float, convert it
                    val = float(vals[1:-1][0])
                except ValueError:
                    val = vals[1:-1][0]
            elif len(vals[1:-1]) == 0:
                val = []
            else:
                val = vals[1:-1][0]
            parm_dict[key] = val
        return parm_dict

    def can_read(self):
        """
        Tests whether or not the provided file has a .asc extension
        Returns
        -------

        """

        return super(NanonisDatReader, self).can_read(extension='dat')
