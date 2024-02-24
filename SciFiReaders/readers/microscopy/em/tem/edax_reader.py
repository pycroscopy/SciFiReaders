#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

################################################################################
# Python class for reading EDAX .h5 files into sidpy Dataset
# and extracting all metadata
#
# Written by Gerd Duscher, UTK 2023
#
# Works for python 3
#
################################################################################

import struct
import h5py
# from warnings import warn
import sys
import numpy as np
import os

import sidpy

__all__ = ["EDAXReader", "version"]

version = '0.1beta'

debugLevel = 0  # 0=none, 1-3=basic, 4-5=simple, 6-10 verbose

if sys.version_info.major == 3:
    unicode = str

# ### utility functions ###




def get_dataset_keys(h5_object):
    if not isinstance(h5_object, (h5py.Group, h5py.File)):
        raise TypeError('h5_object should be a h5py.File or h5py.Group object')

    dataset_list = []
    h5_object.visit(lambda key : dataset_list.append(key) if isinstance(h5_object[key], h5py.Dataset) else None)
    return dataset_list


def reader(h5_file):
    base_group = h5_file[list(h5_file.keys())[0]]
    all_datasets_list = get_dataset_keys(base_group)
    
    datasets = {}
    # read spectum  images first
    for dataset_item in all_datasets_list:
        print(dataset_item)
        if 'Live Map' in dataset_item:
            if 'SPD' in dataset_item:
                dataset = read_spectrum_image(base_group, dataset_item)

def read_metadata_array(structured_array):
    metadata = {}
    for i in range(len(structured_array.dtype.fields)):
        # print(structured_array.dtype.names[i], structured_array[structured_array.dtype.names[i]])
        metadata[structured_array.dtype.names[i]] = structured_array[structured_array.dtype.names[i]]
    return(metadata)

def read_spectrum_image(base_group, dataset_item):
    group_end = dataset_item.index('/SPD')
    dataset = sidpy.Dataset.from_array(base_group[dataset_item][:])
    if dataset.ndim !=3:
        print('Error reading spectrum image')
    dataset.original_metadata = read_metadata_array(base_group[dataset_item[:group_end]+'/SPC'][:])
    dataset.original_metadata.update(dict(base_group[dataset_item].attrs))
    # print(dataset.original_metadata['StartEnergy'], dataset.original_metadata['EndEnergy'])
    # print(dataset.shape[2]/dataset.original_metadata['EndEnergy'])
    # print(dataset.shape[2]*dataset.original_metadata['evPerChannel'] )
    # print(dataset.original_metadata['MicronPerPixelX'], dataset.original_metadata['MicronPerPixelY'])


    dataset.title = dataset_item[:group_end].replace('/', '_').replace(' ','')+'_SpectrumImage'
    dataset.data_type = 'spectral_image'
    dataset.set_dimension(0, sidpy.Dimension(np.arange(dataset.shape[0])* dataset.original_metadata['MicronPerPixelX']*1000,
                                                        name='x', units='nm',
                                                        quantity='distance',
                                                        dimension_type='spatial'))
    dataset.set_dimension(1, sidpy.Dimension(np.arange(dataset.shape[1])* dataset.original_metadata['MicronPerPixelY']*1000,
                                                          name='y', units='nm',
                                                          quantity='distance',
                                                          dimension_type='spatial'))
    dataset.set_dimension(2, sidpy.Dimension(np.arange(dataset.shape[2])* dataset.original_metadata['evPerChannel'],
                                                          name='energy_scale', units='eV',
                                                          quantity='energy',
                                                          dimension_type='spectral'))

    dataset.units = 'counts'
    dataset.quantity = 'intensity'
    
    # print(dataset.title)

    return dataset


def read_image(base_group, dataset_item):
    dataset = sidpy.Dataset.from_array(base_group[dataset_item][:])

    if dataset.ndim !=2:
        print('Error reading image')
    
    if dataset_item[-4:] == '.dat':
        dataset.original_metadata = read_metadata_array(base_group[dataset_item[:-3]+'ipr'][:])
        dataset.original_metadata.update(dict(base_group[dataset_item].attrs))
        dataset.title = dataset_item[:-4].replace('/', '_').replace(' ','')
    elif 'MAPIMAGE' in dataset_item:
        group_end = dataset_item.index('/MAPIMAGE')
        dataset.original_metadata = read_metadata_array(base_group[dataset_item[:group_end]+'/MAPIMAGEIPR'][:])
        dataset.original_metadata.update(read_metadata_array(base_group[dataset_item[:group_end]+'/MAPIMAGECOLLECTIONPARAMS'][:]))
        dataset.original_metadata.update(dict(base_group[dataset_item].attrs))
        dataset.title = dataset_item[:group_end].replace('/', '_').replace(' ','')+'_Image'
    elif 'FOVIMAGE' in dataset_item:
        group_end = dataset_item.index('/FOVIMAGE')
        dataset.original_metadata = read_metadata_array(base_group[dataset_item[:group_end]+'/FOVIPR'][:])
        dataset.original_metadata.update(read_metadata_array(base_group[dataset_item[:group_end]+'/FOVIMAGECOLLECTIONPARAMS'][:]))
        dataset.original_metadata.update(dict(base_group[dataset_item].attrs))
        dataset.title = dataset_item[:group_end].replace('/', '_').replace(' ','')+'_SurveyImage'

    dataset.data_type = 'image'
    dataset.units = 'counts'
    dataset.quantity = 'intensity'
    
    dataset.set_dimension(0, sidpy.Dimension(np.arange(dataset.shape[0])* dataset.original_metadata['MicronsPerPixelX']*1000,
                                                        name='x', units='nm',
                                                        quantity='distance',
                                                        dimension_type='spatial'))
    dataset.set_dimension(1, sidpy.Dimension(np.arange(dataset.shape[1])* dataset.original_metadata['MicronsPerPixelY']*1000,
                                                        name='y', units='nm',
                                                        quantity='distance',
                                                        dimension_type='spatial'))
    return dataset
           
class EDAXReader(sidpy.Reader):
    """
    Creates an instance of EDAXReader which can read one or more HDF5
    datasets formatted in the EDAX format

    We can read Images, and SpectrumStreams (SpectrumImages and Spectra).
    Please note that all original metadata are retained in each sidpy dataset.

    Parameters
    ----------
    file_path : str
        Path to a EDAX file
    Return
    ------
    datasets: dict
        dictionary of sidpy.Datasets
    """

    def __init__(self, file_path, verbose=False):
        """
        file_path: filepath to dm3 file.
        """

        super().__init__(file_path)

        # initialize variables ##
        self.verbose = verbose
        self.__filename = file_path

        path, file_name = os.path.split(self.__filename)
        self.basename, self.extension = os.path.splitext(file_name)
        self.datasets = {}
        
        if 'h5' in self.extension:
            try:
                h5_file = h5py.File(self.__filename, mode='r')
                if not isinstance(h5_file, h5py.File):
                    raise TypeError("File {} does not seem to be of EDAX`s .h5 format".format(self.__filename))
        
                if len(h5_file.keys()) != 1:
                    raise TypeError("File {} does not seem to be of EDAX`s .h5 format".format(self.__filename))
                
                base_metadata = dict(h5_file[list(h5_file.keys())[0]].attrs)
                edax_file = False
                if 'Company' in base_metadata:
                    if base_metadata['Company'] == 'EDAX, LLC':
                        edax_file =True
                if not edax_file:
                    raise TypeError("File {} does not seem to be of EDAX`s .h5 format".format(self.__filename))
                h5_file.close()
            except IOError:
                raise IOError("File {} does not seem to be of EDAX's .h5 format".format(self.__filename))

    def read(self):
        if 'h5' in self.extension:
            # TODO: use lazy load for large datasets
            self.__f = h5py.File(self.__filename, 'r')
            base_group = self.__f[list(self.__f.keys())[0]]
            all_datasets_list = get_dataset_keys(base_group)
    
            for dataset_item in all_datasets_list:
                if 'Live Map' in dataset_item:
                    if 'SPD' in dataset_item:
                        dataset = read_spectrum_image(base_group, dataset_item)
                        self.datasets[dataset.title] = dataset
                        group_end = dataset_item.index('/SPD')
                        self.extract_crucial_metadata(dataset.title)
                        if dataset_item[:group_end]+'/MAPIMAGE' in all_datasets_list:
                            image_dataset = read_image(base_group, dataset_item[:group_end]+'/MAPIMAGE')
                            self.datasets[image_dataset.title] = image_dataset
                            self.extract_crucial_metadata(image_dataset.title)
                        parent_group = dataset_item.index('/Live Map')
                        if dataset_item[:parent_group]+'/FOVIMAGE' in all_datasets_list:
                            image_dataset = read_image(base_group,dataset_item[:parent_group]+'/FOVIMAGE')
                            self.datasets[image_dataset.title] = image_dataset
                            self.extract_crucial_metadata(image_dataset.title)
                        for item in all_datasets_list:    
                            if dataset_item[:-3]+'ROIs' in item:
                                if item[-3:] == 'dat':
                                    image_dataset = read_image(base_group,item)
                                    self.datasets[image_dataset.title] = image_dataset
                                    self.extract_crucial_metadata(image_dataset.title)

            self.__f.close()
            return self.datasets

    def get_filename(self):
        return self.__filename

    filename = property(get_filename)


    def get_tags(self):
        return self.original_metadata

    tags = property(get_tags)

    def get_datasets(self):
        return self.datasets 

    def extract_crucial_metadata(self, key):
        """Read essential parameter from original_metadata originating from a Nion file"""
        
        original_metadata = self.datasets[key].original_metadata

        if not isinstance(original_metadata, dict):
            raise TypeError('We need a dictionary to read')
        
        experiment = {'stage': {},
                      'detector': {},
                      'microscope': {},
                      'analysis': {}}

        if 'KVolt' in original_metadata:
            experiment['microscope']['acceleration_voltage_V'] = original_metadata['KVolt']*100
        if 'KV' in original_metadata:
            experiment['microscope']['acceleration_voltage_V'] = original_metadata['KV']*1000
        if 'WorkingDistance' in original_metadata:
            experiment['stage']['working_distance'] = original_metadata['WorkingDistance']/1000
        if 'LiveTime' in original_metadata:
            experiment['detector']['live_time'] = original_metadata['LiveTime']
        if 'TiltAngle' in original_metadata:
            experiment['detector']['tilt_angle'] = original_metadata['TiltAngle']
        if 'TakeOffAngle' in original_metadata:
            experiment['detector']['take_off_angle'] = original_metadata['TakeOffAngle']
        if 'DetectorResoultion' in original_metadata:
            experiment['detector']['resolution'] = original_metadata['DetectorResoultion']
        if 'AlThickness' in original_metadata:
            experiment['detector']['Al_thickness'] = original_metadata['AlThickness'] * 1e-6 # in m
        if 'BeWinThickness' in original_metadata:
            experiment['detector']['Be_thickness'] = original_metadata['BeWinThickness'] * 1e-6 # in m
        if 'ParThickness' in original_metadata:
            experiment['detector']['Par_thickness'] = original_metadata['ParThickness'] * 1e-6 # in m
        if 'AuThickness' in original_metadata:
            experiment['detector']['Au_thickness'] = original_metadata['AuThickness'] * 1e-6 # in m
        if 'SiDeadThickness' in original_metadata:
            experiment['detector']['Si_dead_layer_thickness'] = original_metadata['SiDeadThickness'] * 1e-6 # in m
        if 'SiLiveThickness' in original_metadata:
            experiment['detector']['Si_live_thickness'] = original_metadata['SiLiveThickness'] # in m
            
        if 'XRayIncidenceAngle' in original_metadata:
            experiment['detector']['x_ray_incident_angle'] = original_metadata['XRayIncidenceAngle']
        if 'AzimuthAngle' in original_metadata:
            experiment['detector']['azimuth_angle'] = original_metadata['AzimuthAngle']
        if 'ElevationAngle' in original_metadata:
            experiment['detector']['elevation_angle'] = original_metadata['ElevationAngle']
        if 'BCoefficient' in original_metadata:
            experiment['detector']['b_coefficient'] = original_metadata['BCoefficient']
        if 'CCoefficient' in original_metadata:
            experiment['detector']['c_coefficient'] = original_metadata['CCoefficient']

        if 'XTiltAngle' in original_metadata:
            experiment['stage']['x_tilt_angle'] = original_metadata['XTiltAngle']
        if 'YTiltAngle' in original_metadata:
            experiment['stage']['y_tilt_angle'] = original_metadata['YTiltAngle']
        if 'Tilt' in original_metadata:
            experiment['stage']['tilt'] = original_metadata['Tilt']/10
        
        if 'AtomicNumberOfPeakIds' in original_metadata:
            experiment['analysis']['atomic_numbers'] = original_metadata['AtomicNumberOfPeakIds']
        if 'EnergyOfPeakIds' in original_metadata:
            experiment['analysis']['peak_energies'] = original_metadata['EnergyOfPeakIds']
        if 'WeightFraction'in original_metadata:
            experiment['analysis']['weight_fractions'] = original_metadata['WeightFraction']
        
        self.datasets[key].metadata['experiment'] = experiment


