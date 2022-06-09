# -*- coding: utf-8 -*-
"""
Created on Wed Dec 07 16:04:34 2016

Updated on Fri Sep 11 15:22:00 2020 for ScopeReader

@author: Suhas Somnath, Chris R. Smith, Raj Giridhargopal, Rama Vasudevan
"""

from __future__ import division, print_function, absolute_import, unicode_literals
import sys
import numpy as np  # For array operations
import sidpy as sid
from sidpy.sid import Reader
import h5py
import os
import re

if sys.version_info.major == 3:
    unicode = str

# Reader Information
# ----------------------
reader_name = 'ARHDF5'
description = 'Asylum Research HDF5 file typically used for storing spatial maps of force-distance curves'

class ARhdf5Reader(Reader):
    """
    Extracts data and metadata from ARhdf5 files
    These are Asylum Research files typically captured for
    force maps from their microscopes.
    The ARhdf5 file should be generated with the converter provided
    by Asylum Research called ARDFtoHDF5. Contact David Aue <David.Aue@oxinst.com>
    or Tommaso Costanzo <tommaso.costanzo01@gmail.com> to get a
    copy of the converter. NOTE: the AR converter works only under
    windows.

    NOTE: At this point, the z dimension vector is not correctly captured
    Not immediately clear how to fix it. TODO: Check with Asylum
    """

    def read(self, verbose=False):
        """
        Reads the file given in file_path into a sidpy dataset

        Parameters
        ----------
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging
        debug : Boolean (Optional)
            Whether or not to print log statements
        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Multi-channel inputs are separated into individual dataset objects
        """
        file_path = self._input_file_path

        self.notes = None
        self.segments = None
        self.segments_name = []
        self.map_size = {'X': 0, 'Y': 0}
        self.channels_name = []
        self.points_per_sec = None
        self.verbose = verbose

        # Open the datafile
        try:
            data_filepath = os.path.abspath(file_path)
            ARh5_file = h5py.File(data_filepath, 'r')
        except:
            print('Unable to open the file', data_filepath)
            raise

        # Get info from the origin file like Notes and Segments
        decode_text = True
        if type(ARh5_file.attrs['Note']) is str: decode_text = False
        
        if decode_text: self.notes = ARh5_file.attrs['Note'].decode('utf-8')
        else: self.notes = ARh5_file.attrs['Note']

        self.segments = ARh5_file['ForceMap']['0']['Segments']
        segments_name = list(ARh5_file['ForceMap']['0'].attrs['Segments'])
        
        if decode_text: self.segments_name = [name.decode('utf-8') for name in segments_name]
        else: self.segments_name = [name for name in segments_name]

        self.map_size['X'] = ARh5_file['ForceMap']['0']['Segments'].shape[0]
        self.map_size['Y'] = ARh5_file['ForceMap']['0']['Segments'].shape[1]
        channels_name = list(ARh5_file['ForceMap']['0'].attrs['Channels'])
        if decode_text: self.channels_name = [name.decode('utf-8') for name in channels_name]
        else: self.channels_name = [name for name in channels_name]

        try:
            self.points_per_sec = np.float(self.note_value('ARDoIVPointsPerSec'))
        except NameError:
            self.points_per_sec = np.float(self.note_value('NumPtsPerSec'))

        if self.verbose:
            print('Map size [X, Y]: ', self.map_size)
            print('Channels names: ', self.channels_name)
            print('Name of Segments:', self.segments_name)

        # Only the extension 'Ext' segment can change size
        # so we get the shortest one and we trim all the others

        extension_idx = self.segments_name.index('Ext')
        short_ext = np.amin(np.array(self.segments[:, :, extension_idx]))
        longest_ext = np.amax(np.array(self.segments[:, :, extension_idx]))
        difference = longest_ext - short_ext  # this is a difference between integers
        tot_length = (np.amax(self.segments) - difference) + 1
        # +1 otherwise array(tot_length) will be of 1 position shorter
        points_trimmed = np.array(self.segments[:, :, extension_idx]) - short_ext

        # Open the output hdf5 file
        x_dim = np.linspace(0, np.float(self.note_value('FastScanSize')),
                            self.map_size['X'])
        y_dim = np.linspace(0, np.float(self.note_value('FastScanSize')),
                            self.map_size['Y'])
        z_dim = np.arange(tot_length) / np.float(self.points_per_sec)

        datasets = [] #list of sidpy datasets

        #Let's get all the metadata
        # Create the new segments that will be stored as attribute
        new_segments = {}
        for seg, name in enumerate(self.segments_name):
            new_segments.update({name: self.segments[0, 0, seg] - short_ext})

        seg_metadata = {'Segments': new_segments,
                                           'Points_trimmed': points_trimmed,
                                           'Notes': self.notes}
        general_metadata = {'translator': 'ARhdf5',
                            'instrument': 'Asylum Research ' + self.note_value('MicroscopeModel'),
                            'AR sftware version': self.note_value('Version')}

        combined_metadata = dict({'segments': seg_metadata, 'general': general_metadata})

        for index, channel in enumerate(self.channels_name):
            main_dset = np.empty((self.map_size['X'], self.map_size['Y'], tot_length))
            for column in np.arange(self.map_size['X']):
                for row in np.arange(self.map_size['Y']):
                    AR_pos_string = str(column) + ':' + str(row)
                    seg_start = self.segments[column, row, extension_idx] - short_ext
                    main_dset[column, row, :] = ARh5_file['ForceMap']['0'][AR_pos_string][index, seg_start:]

            quant_unit = self.get_def_unit(channel)

            data_set = sid.Dataset.from_array(main_dset, name='Image')
            data_set.data_type = sid.DataType.SPECTRAL_IMAGE

            # Add quantity and units
            data_set.units = quant_unit
            data_set.quantity = channel

            # Add dimension info
            data_set.set_dimension(0, sid.Dimension(x_dim,
                                                    name='x',
                                                    units='m', quantity='x',
                                                    dimension_type='spatial'))
            data_set.set_dimension(1, sid.Dimension(y_dim,
                                                    name='y',
                                                    units='m', quantity='y',
                                                    dimension_type='spatial'))
            data_set.set_dimension(2, sid.Dimension(z_dim,
                                                    name='Time',
                                                    units='s', quantity='z',
                                                    dimension_type='spectral'))

            # append metadata
            chan_metadata = dict(ARh5_file['ForceMap']['0'].attrs)
            new_dict = {**chan_metadata, **combined_metadata}
            data_set.metadata = new_dict

            # Finally, append it
            datasets.append(data_set)

        for index, image in enumerate(ARh5_file['Image'].keys()):
            main_dset = np.array(ARh5_file['Image'][image])

            quant_unit = self.get_def_unit(image)

            data_set = sid.Dataset.from_array(main_dset, name='Image')
            data_set.data_type = sid.DataType.IMAGE

            # Add quantity and units
            data_set.units = quant_unit
            data_set.quantity = channel

            # Add dimension info
            data_set.set_dimension(0, sid.Dimension(x_dim,
                                                    name='x',
                                                    units=quant_unit, quantity='x',
                                                    dimension_type='spatial'))
            data_set.set_dimension(1, sid.Dimension(y_dim,
                                                    name='y',
                                                    units=quant_unit, quantity='y',
                                                    dimension_type='spatial'))

            # append metadata
            chan_metadata = dict(ARh5_file['Image'].attrs)
            new_dict = {**chan_metadata, **combined_metadata}
            data_set.metadata = new_dict

            # Finally, append it
            datasets.append(data_set)

        # Return the dataset
        return datasets

    def can_read(self):
        """
        Tests whether or not the provided file has a .ibw extension
        Returns
        -------

        """
        file_path = self._input_file_path
        extension = os.path.splitext(file_path)[1][1:]
        if extension not in ['hdf5', 'h5']:
            return False
        try:
            h5_f = h5py.File(file_path, 'r')
        except:
            return False
        if 'ForceMap' not in h5_f.keys():
            return False
        if not isinstance(h5_f['ForceMap'], h5py.Group):
            return False
        return

    def note_value(self, name):
        '''
        Get the value of a single note entry with name "name"

        Parameters
        ----------------
        name : String / unicode
            Name of the parameter to get teh value

        Returns
        ----------------
        value : String / unicode
            Value of the Note entry requested.
        '''
        try:
            match = re.search(r"^" + name + ":\s+(.+$)", self.notes, re.M)
            if not match:
                raise Exception
        except:
            match = re.search(r"^" + name + ":+(.+$)", self.notes, re.M)
        if (match):
            matched = match.groups()
            if len(matched) == 1:
                return match.groups()[0]
            else:
                # We do not expect to enter here
                print('WARNING! Multiple value matched! \n Only the first is returned')
                return match.groups()[0]
        else:
            raise NameError('Note entry with name "{}" not found'.format(name))

    def get_def_unit(self, chan_name):
        """
        Retrive the default unit from the channel name

        Parameters
        ----------
        chan_name : string
            Name of the channel to get the unit

        Returns
        -------
        default_unit : string
            Default unit of that channel
        """

        # Check if chan_name is string
        if not isinstance(chan_name, (str, unicode)):
            raise TypeError('The channel name must be of type string')

        # Find the default unit
        if chan_name.startswith('Phas'):
            default_unit = 'deg'
        elif chan_name.startswith('Curr'):
            default_unit = 'A'
        elif chan_name.startswith('Freq'):
            default_unit = 'Hz'
        elif chan_name.startswith('Bias'):
            default_unit = 'V'
        elif (chan_name.startswith('Amp') or
              chan_name.startswith('Raw') or
              chan_name.startswith('ZSnsr') or
              chan_name.startswith('Defl') or
              chan_name.startswith('MapHeight')):
            default_unit = 'm'
        elif (chan_name.startswith('Seconds') or
              chan_name == 'TriggerTime'):
            default_unit = 's'
        elif chan_name.startswith('HeaterTemperature'):
            default_unit = 'Celsius'
        elif chan_name == 'MapAdhesion':
            default_unit = 'N/m^2'
        elif chan_name == 'HeaterHumidity':
            default_unit = 'g/m^3'
        elif chan_name.endswith('LVDT'):
            # This should be the laser virtual deflection
            default_unit = 'm'
        else:
            if self.debug:
                print('Unknown unit for channel: {}'.format(chan_name))
                print('Unit set to "unknown"')
            default_unit = 'unknown'

        return default_unit
