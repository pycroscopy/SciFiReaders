# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 15:39:00 202`0`

@author: Rama Vasudevan
"""

from __future__ import division, print_function, absolute_import, unicode_literals
import sys
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
import re
from os import path

if sys.version_info.major == 3:
    unicode = str

class NanonisDatReader(Reader):
    """
    Reads files obtained via Nanonis controllers in .dat files.
    These are generally point spectroscopy measurements.

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
            Multi-channel inputs are separated into individual dataset objects
        """

        file_path = self._input_file_path
        folder_path, file_name = path.split(file_path)
        file_name = file_name[:-4]

        # Extracting the raw data into memory
        file_handle = open(file_path, 'r')
        string_lines = file_handle.readlines()
        file_handle.close()

        data_start = string_lines.index('[DATA]\n')
        header = string_lines[:data_start - 1]

        channel_names = string_lines[data_start+1].split('\t')
        channel_units = [re.search(r'\((.*?)\)',channel_names[ind]).group(1) for ind in range (len(channel_names))]

        # Extract parameters from the first few header lines
        parm_dict= self._read_parms(header)

        # Extract the STS data from subsequent lines
        raw_data = np.loadtxt(file_path, skiprows=data_start+2)

        # Generate the x / voltage / spectroscopic axis:
        volt_vec = raw_data[:,0]

        datasets = [] #list of sidpy datasets that will be output

        # Add quantity and units
        for chan_ind, chan_name in enumerate(channel_names[1:]): #start from 1 because 0th column is the spectral one
            # now write it to the sidpy dataset object
            data_set = sid.Dataset.from_array(raw_data[:,chan_ind+1], name='Nanonis_Dat_File')
            data_set.data_type = 'spectrum'
            data_set.units = channel_units +1
            data_set.quantity = 'Current'

            # Add dimension info
            data_set.set_dimension(0, sid.Dimension(volt_vec, name=chan_name,
                                                    units=channel_units[0], quantity='Voltage',
                                                    dimension_type=sid.DimensionType.SPECTRAL))

            # append metadata
            data_set.metadata = parm_dict
            datasets.append(data_set)

        # Return the sidy dataset
        return datasets

    @staticmethod
    def _read_parms(string_lines):
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

        def parse_header(header):
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
                else:
                    val = vals[1:-1][0]
                parm_dict[key] = val
            return parm_dict

        def parse_parm(line):
            # ".  .  Auto_Flush_Period = 0.1 Second"
            match_obj = re.match(r'\.  \.  (.*) = (.*)', line, re.M | re.I)
            type_list = [str, str]
            if match_obj:
                raw_vals = [type_caster(match_obj.group(ind)) for ind, type_caster in
                            zip(range(1, 1 + len(type_list)), type_list)]

                # Some cleaning:
                raw_vals[0] = raw_vals[0].replace('-', '_').strip()  # We use '-' as a level separator
                raw_vals[1] = raw_vals[1].replace('--', '').strip()

                # often, units are on the values side, see if these can be transitioned over to the key:
                vals_split = raw_vals[1].split(' ')
                if len(vals_split) == 2:
                    raw_vals = [raw_vals[0] + ' [' + vals_split[1] + ']', vals_split[0]]
                try:
                    raw_vals[1] = float(raw_vals[1])
                    # convert those values that should be integers:
                    if raw_vals[1] % 1 == 0:
                        raw_vals[1] = int(raw_vals[1])
                except ValueError:
                    pass
                return {raw_vals[0]: raw_vals[1]}
            else:
                return None

        def flatten_dict(nested_dict, separator='-'):
            # From: https://codereview.stackexchange.com/questions/21033/flatten-dictionary-in-python-functional-style
            def expand(outer_key, outer_value):
                if isinstance(outer_value, dict):
                    return [(outer_key + separator + inner_key, inner_value) for inner_key, inner_value in flatten_dict(outer_value).items()]
                else:
                    return [(outer_key, outer_value)]

            items = [item for outer_key, outer_value in nested_dict.items() for item in expand(outer_key, outer_value)]

            return dict(items)

        # #############################################################################################################

        temp_dict = dict()

        line = string_lines[1]
        if line.startswith('# Created by SPIP'):
            line = line.replace('# Created by SPIP ', '').replace('\n', '')
            ind = line.index(' ')
            temp_dict['SPIP_version'] = line[:ind]
            temp_dict['creation_time'] = line[ind + 1:]

        # #################################################################################################

        line_offset = 3
        for line_ind, line in enumerate(string_lines[line_offset:]):
            if parse_header(line) is not None:
                line_offset += line_ind
                break
            line = line.replace('# ', '')
            line = line.replace('\n', '')
            temp = line.split('=')
            test = temp[1].strip()
            try:
                test = float(test)
                # convert those values that should be integers:
                if test % 1 == 0:
                    test = int(test)
            except ValueError:
                pass
            temp_dict[temp[0].strip().replace('-', '_')] = test

        main_dict = {'Main': temp_dict.copy()}

        # #################################################################################################

        curr_cat_name = None
        temp_dict = dict()

        for ind, line in enumerate(string_lines[line_offset:]):
            if line.strip().startswith('# Start of Data:'):
                line_offset += ind + 1
                break
            header_name = parse_header(line)
            if header_name:
                if curr_cat_name is not None:
                    main_dict[curr_cat_name] = temp_dict.copy()
                    temp_dict = dict()
                curr_cat_name = header_name
            else:
                this_parm = parse_parm(line)
                if this_parm is None:
                    continue
                temp_dict.update(this_parm)
        if len(temp_dict) > 0:
            main_dict[curr_cat_name] = temp_dict.copy()

        # #################################################################################################

        return flatten_dict(main_dict), line_offset

    def can_read(self):
        """
        Tests whether or not the provided file has a .asc extension
        Returns
        -------

        """

        return super(NanonisDatReader, self).can_read(extension='dat')
