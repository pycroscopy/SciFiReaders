# -*- coding: utf-8 -*-
"""
Created on Tue Oct 20 15:39:40 2020

@author: 4sv
"""

from __future__ import division, print_function, absolute_import, unicode_literals
import h5py
import warnings
import sidpy
from sidpy.sid import Reader

try:
    import pyUSID as usid
except ModuleNotFoundError:
    usid = None


class Usid_reader(Reader):
    
    
    debugLevel = 0
    
    def __init__(self, file_path, verbose=False):
        
        """
        Parameters
        ----------
        
        file_path : str 
            path to the file containing USID Dataset.
        verbose: bool
        
        Attributes
        ----------
        self._input_file_path: str
            path provided to the file containing USID Dataset
        self._file: HDF5 file opened in 'r' mode
        
        
        Returns
        -------
        NONE (Initializes the class attributes)
        """
        
        super(Usid_reader, self).__init__(file_path)
        self.verbose = verbose
        
        if not usid:
            raise ModuleNotFoundError('Please install pyUSID to use this Reader')
        try:
            self._file = h5py.File(self._input_file_path, mode = 'r')
        except FileNotFoundError:
            raise FileNotFoundError('File not found')
        
        
        
        
    def _get_maindatasets(self):
        """
        Gets the maindatasets in the paths provided
        If the dataset path is not provided, gets all the datasets in the file 
        using usid.hdf_utils.get_all_main()
        
        Raises an error if no main datasets are found
        
        Attributes
        ----------
        self._main_datasets: list
            list of all main USID datasets found in the file path
        
        Returns
        -------
        NONE (writes all the maindatasets in the path to attribute self._main_datasets)
        """
        
        if self._dataset_path is not None:
            self._main_datasets = []
            
            if type(self._dataset_path) == list:
                for dataset in self._dataset_path:
                    if usid.hdf_utils.check_if_main(self._file[dataset]):
                        self._main_datasets.append(usid.USIDataset(self._file[dataset]))
                    else:
                        warnings.warn('{} is not a main dataset'.format(dataset))
                        
            elif type(self._dataset_path) == str:
                if usid.hdf_utils.check_if_main(self._file[self._dataset_path]):
                    self._main_datasets.append(usid.USIDataset(self._file[self._dataset_path]))
                else:
                    warnings.warn('{} is not a main dataset'.format(self._dataset_path))
                
            
            else:
                raise TypeError('Provide a path (StringType) to the main dataset or a List of paths')
            
        else:
            self._main_datasets = usid.hdf_utils.get_all_main(self._file)
        
        
        
        if len(self._main_datasets) == 0:
            raise TypeError('There are no main USID datasets in this file')
        
        
        
    @staticmethod
    def _get_dimension_descriptors(main_dataset, verbose):
        
        """
        Parameters
        ----------
        main_dataset: USID main dataset
            
        verbose: bool
        
        Gets the dimension descriptors for the maindataset provided as the
        argument
        
        
        Returns
        -------
        dims: list
        dim_labels: list
        dim_types: list
            spectral or spatial
        dim_quantities: list
        dim_units: list
            list of units of each dimension
        dim_values: list
            list of values at which the readings are recorded
        """
        
        pos_dim, spec_dim = 0, 0
        dims, dim_labels, dim_types, dim_quantities, dim_units, dim_values = [], [], [], [], [], []
          
        for dim, dim_label in enumerate(main_dataset.n_dim_labels):
            dims.append(dim)
            dim_labels.append(dim_label)
            if dim_label in main_dataset.pos_dim_labels:
                dim_types.append('spatial')
                dim_values.append(main_dataset.get_pos_values(dim_label))
                descriptor = main_dataset.pos_dim_descriptors[pos_dim].split('(')
                if descriptor[1][0] != ')':
                    dim_quantities.append(descriptor[0][:-1])
                    dim_units.append(descriptor[1][:-1])
                else:
                    dim_quantities.append(descriptor[0][:-1])
                    dim_units.append('generic')
                pos_dim += 1
                
            else:
                dim_types.append('spectral')
                dim_values.append(main_dataset.get_spec_values(dim_label))
                descriptor = main_dataset.spec_dim_descriptors[spec_dim].split('(')
                if descriptor[1][0] != ')':
                    dim_quantities.append(descriptor[0][:-1])
                    dim_units.append(descriptor[1][:-1])
                else:
                    dim_quantities.append(descriptor[0][:-1])
                    dim_units.append('generic')
                spec_dim += 1
            if verbose:
                print('Read dimension {} of  type {} as {} ({})'.format(dim_labels[dim], dim_types[dim],
                                                                    dim_quantities[dim], dim_units[dim]))
        
        return dims, dim_labels, dim_types, dim_quantities, dim_units, dim_values
    
    @staticmethod
    def _get_main_data_descriptors(main_dataset):
        
        """
        Gets the descriptors (quatity and units) of the output quantity
        of a non compund main dataset
        
        Parameters
        ----------
        main_dataset: USID main dataset
        Returns
        -------
        qunatity: str
            Name of the output quantity
        Units: str
        """
        
        des = main_dataset.data_descriptor.split('(')
        try:
            des[1]
            quantity = des[0][:-1]
            units = des[1][:-1]
        except IndexError:
            quantity = des[0]
            units = 'generic'
            
        return quantity, units
    
    @staticmethod
    def _get_compound_data_descriptors(name):
        """
        Gets the descriptors (quatity and units) of the output quantity
        of a compund dataset
        
        Parameters
        ----------
        name: str
        
        Returns
        -------
        qunatity: str 
            Name of the output quantity 
        Units: str
        """
        
        des = name.split('[')
        try:
            des[1]
            quantity = des[0][:-1]
            units = des[1][:-1]
        except IndexError:
            quantity = des[0]
            units = 'generic'
            
        return quantity, units
    
    def _get_metadata(main_dataset):
        metadata = {}
        #We get all the attributes corresponding to main_dataset
        atts = sidpy.hdf_utils.get_attributes(main_dataset)
        for attr_name in (atts):
            #We omit h5py reference files
            if not isinstance(atts[attr_name], (h5py.h5r.Reference, h5py.h5r.RegionReference)):
                #We do not want quantity of units either
                if not (attr_name != 'quantity' or attr_name != 'units'):
                    metadata[attr_name] = atts[attr_name]
                    
        return metadata
        
        
    
    
    def read(self, dataset_path = None):
        """
        Parameters
        ----------
        dataset_path: str or list
            path inside the file to the main Dataset or a list of paths
        
        Returns
        -------
        sid_datasets: sidpy dataset or list
        sidpy dataset object when a single dataset is found in the path or list 
        of sidpy dataset objects
        """
        self._dataset_path = dataset_path
        self._get_maindatasets()

        sid_datasets = []
        
        for j,main_dataset in enumerate(self._main_datasets):
            # Check if the main dataset is compound
            if main_dataset.dtype.names is not None:
                #Get descriptors of the main dataset
                dims, dim_labels, dim_types, dim_quantities, dim_units, dim_values = Usid_reader._get_dimension_descriptors(main_dataset, verbose = self.verbose)
                
                for name in (main_dataset.dtype.names):
                    sid_dataset = sidpy.Dataset.from_array(main_dataset.get_n_dim_form()[name])
                    #Get descriptors (units) of the output quantity
                    sid_dataset.quantity, sid_dataset.units = Usid_reader._get_compound_data_descriptors(name)
                    
                    #Set dimensions for the main dataset
                    for i in range(len(dim_labels)):
                        sid_dataset.set_dimension(dims[i], sidpy.Dimension(dim_values[i],name = dim_labels[i],
                                                       units=dim_units[i],
                                                       quantity=dim_quantities[i],
                                                       dimension_type=dim_types[i]))
                    
                    # Dealing with metadata
                    meta_data = Usid_reader._get_metadata(main_dataset)
                    sid_dataset.metadata.update(meta_data)
                    sid_datasets.append(sid_dataset)
            
            #For a non-compound dataset
            else:
                #Get descriptors of the main dataset
                dims, dim_labels, dim_types, dim_quantities, dim_units, dim_values = Usid_reader._get_dimension_descriptors(main_dataset, verbose = self.verbose)
                sid_dataset = sidpy.Dataset.from_array(main_dataset.get_n_dim_form())
                #Get descriptors (units) of each of the output quantity
                sid_dataset.quantity, sid_dataset.units = Usid_reader._get_main_data_descriptors(main_dataset)

                
                #Set dimensions for the main dataset
                for i in range(len(dim_labels)):
                    sid_dataset.set_dimension(dims[i], sidpy.Dimension(dim_values[i],name = dim_labels[i],
                                                       units=dim_units[i],
                                                       quantity=dim_quantities[i],
                                                       dimension_type=dim_types[i]))
                
                meta_data = Usid_reader._get_metadata(main_dataset)
                sid_datasets.append(sid_dataset)
                    
            
                

        
        if len(sid_datasets) == 1:
            sid_datasets = sid_datasets[0]
            

        return sid_datasets
    
    
    def can_read(self):
        """
        Tests whether or not the provided file has a .h5 extension
        Returns
        -------
        """
        pass   