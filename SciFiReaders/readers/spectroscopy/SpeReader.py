# -*- coding: utf-8 -*-
"""
SpeReader is designed to read a single Raman spectra from a Princeton Instruments CCD camera.
The reader takes in the Princeton Instruments .SPE file and produces a sidpy dataset.

Created on Fri May 14 2020

@author: Sumner Harris
"""

import numpy as np
import re
from sidpy import Dataset, Dimension, Reader

class RamanSpeReader(Reader):
    
    def read(self):
        """
        Reads a single Raman spectra from a Princeton Instruments CCD camera.

        Returns
        -------
        data_set: sidpy.Dataset object
            wraps all the raw data and metadata from the input file into a Dataset object
        
        """
        # open the .SPE file
        with open(self._input_file_path, 'rb') as f:
            lines = f.readlines()
            # Create an empty dictionary for the metadata
            metadata_dictionary = {}

            # Search through the file for the needed metadata
            metadata_dictionary['date_acquired'] = re.search(b'date="(.*?)"', lines[1])[1].decode('ANSI')  
            metadata_dictionary['width'] = int(re.search(b'width="(.*?)"', lines[1])[1])
            metadata_dictionary['height'] = int(re.search(b'height="(.*?)"', lines[1])[1])
            metadata_dictionary['size'] = metadata_dictionary['width']*metadata_dictionary['height']
            metadata_dictionary['exposure_time'] = int(re.search(b'<ExposureTime type="Double">(.*?)</ExposureTime>', lines[1])[1])
            metadata_dictionary['excitation_wavelength'] = float(re.search(b'laserLine="(.*?)"',lines[1])[1])
            metadata_dictionary['center_wavelength'] = float(re.search(b'<CenterWavelength type="Double">(.*?)</CenterWavelength>',lines[1])[1])
            metadata_dictionary['orientation'] = re.search(b'orientation="(.*?)"',lines[1])[1].decode('ANSI')

            # Get the wavelength and intensity
            wavelength_string = re.search(b'<Wavelength xml:space="preserve">(.*?)</Wavelength>',lines[1])[1].decode('utf-8')
            wavelength = np.array(wavelength_string.split(','), dtype=np.float64)

            f.seek(4100)
            intensity = np.fromfile(f,dtype=np.float32,count=metadata_dictionary['size'])

            raman_shift_wavenumbers = 1e7*(1/metadata_dictionary['excitation_wavelength'] - 1/wavelength)

            f.close()
            
        # create the sidpy dataset
        data_set = Dataset.from_array(intensity, name='Raman Spectra')

        data_set.data_type = 'spectrum'
        data_set.units = 'counts'
        data_set.quantity = 'Intensity'

        # set dimensions
        data_set.set_dimension(0, Dimension(raman_shift_wavenumbers, name='Raman Shift',
                                                 units = 'cm-1',
                                                 quantity='Raman shift',
                                                 dimension_type='spectral'))
        data_set.set_dimension(1, Dimension(intensity, name='Intensity',
                                                 units = 'counts',
                                                 quantity='intensity',
                                                 dimension_type='spectral'))        

        data_set.metadata = metadata_dictionary

        return data_set
    
    def can_read(self):
        """
        Tests whether or not the provided file has .spe extension

        Returns
        -------
        """

        return super(RamanSpeReader, self).can_read(extension='spe')
