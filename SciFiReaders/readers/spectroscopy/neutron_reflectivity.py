# -*- coding: utf-8 -*-
"""
Neutron reflectivity captured at SNS comes in this format.

Created on Fri  Jun 21 2024

@author: Rama Vasudevan
"""

import numpy as np
import re
from sidpy import Dataset, Dimension, Reader

class NeutronReflectivity(Reader):
    
    def read(self):
        """
        Reads a single neutron reflectivity curve, acquired at SNS/ORNL.

        Returns
        -------
        data_set: sidpy.Dataset object
            wraps all the raw data and metadata from the input file into a Dataset object
        
        """
        self.file_path = self._input_file_path
        metadata, headings, data = self._read_data()
      
        # create the sidpy dataset
        data_set = Dataset.from_array(data[:,1], name='Neutron Reflectivity')

        data_set.data_type = 'spectrum'
        data_set.units = str(headings[1][1])
        data_set.quantity = str(headings[1][0])

        # set dimensions
        data_set.set_dimension(0, Dimension(data[:,0], name=str(headings[0][0]),
                                                    units = str(headings[0][1]),
                                                    quantity=str(headings[0][0]),
                                                    dimension_type='spectral'))

        #get the metadata right
        metadata_dict = {}
       
        for line in metadata:
            output = line.split(':')
            if len(output)>1:
                metadata_dict[output[0]] = output[1]
                
        metadata_dict['header'] = metadata
        metadata_dict['column_headings'] = headings
        metadata_dict['raw_data'] = data
        data_set.original_metadata = metadata_dict

        return data_set
    
    def _read_data(self):
        
        with open(self.file_path, 'r') as f:
            header = []
            for ind,line in enumerate(f):
                if '#' in line:
                    header.append(line[2:])

            column_headings = header[-1]
            columns = re.split(r'\s{2,}', column_headings.strip())

            columns_with_units = []

            for column in columns:
                match = re.match(r'([^\[]+)(\s*\[.*\])?', column)
                name = match.group(1).strip()
                unit = match.group(2).strip() if match.group(2) else None
                columns_with_units.append((name, unit))
        
        data = np.loadtxt(self.file_path)
        metadata = header

        return metadata, columns_with_units, data
    
  