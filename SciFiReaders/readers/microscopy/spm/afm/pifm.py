# -*- coding: utf-8 -*-
"""
Created on Mon Sep 13 21:46:14 2021

@author: Rajiv Giridharagopal, rgiri@uw.edu. Based on original
translator in legacy Pycroscopy by Jessica Kong, kongjy@uw.edu
"""

import sidpy as sid
from sidpy.sid import Reader
from sidpy.sid import Dimension

import os
import numpy as np
import h5py

from pyNSID.io.hdf_io import write_nsid_dataset
from pyNSID.io.hdf_io import create_indexed_group, write_simple_attrs

class PiFMTranslator(Reader):
    """
    Class that writes images, spectrograms, point spectra and associated ancillary data sets to h5 file in pyUSID data
    structure.
    """

    def read(self ):
        """
        Parameters
        ----------
        file_path : String / unicode
            Absolute path of the .ibw file
        verbose : Boolean (Optional)
            Whether or not to show  print statements for debugging

        Returns
        -------
        sidpy.Dataset : List of sidpy.Dataset objects.
            Image layers are saved as separate Dataset objects
        """
        
        self.get_path()
        self.read_anfatec_params()
        self.read_file_desc()
        self.read_spectrograms()
        self.read_imgs()
        self.read_spectra()
        self.datasets = self.make_datasets()

        return self.datasets

    def create_h5(self, append_path='', overwrite=False):
        """
        Writes a new HDF5 file with the translated data
        
        append_path : string (Optional)
            h5_file to add these data to, must be a path to the h5_file on disk
        overwrite : bool (optional, default=False)
            If True, will overwrite an existing .h5 file of the same name        
        """
        self.create_hdf5_file(append_path, overwrite)
        self.write_datasets_hdf5()
        
        return
        
    def get_path(self):
        """writes full path, directory, and file name as attributes to class"""
        
        self.path = self._input_file_path
        full_path = os.path.realpath(self.path)
        directory = os.path.dirname(full_path)
        # file name
        basename = os.path.basename(self.path)
        self.full_path = full_path
        self.directory = directory
        self.basename = basename

    def read_anfatec_params(self):
        """reads the scan parameters and writes them to a dictionary"""
        
        params_dictionary = {}
        params = True
        with open(self.path, 'r', encoding="ISO-8859-1") as f:
            for line in f:
                if params:
                    sline = [val.strip() for val in line.split(':')]
                    if len(sline) == 2 and sline[0][0] != ';':
                        params_dictionary[sline[0]] = sline[1]
                    #in ANFATEC parameter files, all attributes are written before file references.
                    if sline[0].startswith('FileDesc'):
                        params = False
            f.close()
        self.params_dictionary = params_dictionary
        self.x_len, self.y_len = int(params_dictionary['xPixel']), int(params_dictionary['yPixel'])

    def read_file_desc(self):
        """reads spectrogram, image, and spectra file descriptions and stores all to dictionary where
        the key:value pairs are filename:[all descriptors]"""
        
        spectrogram_desc = {}
        img_desc = {}
        spectrum_desc = {}
        pspectrum_desc = {}
        
        with open(self.path,'r', encoding="ISO-8859-1") as f:

            lines = f.readlines()
            for index, line in enumerate(lines):

                sline = [val.strip() for val in line.split(':')]
                #if true, then file describes image.

                if sline[0].startswith('FileDescBegin'):
                    no_descriptors = 5
                    file_desc = []

                    for i in range(no_descriptors):

                        line_desc = [val.strip() for val in lines[index+i+1].split(':')]
                        file_desc.append(line_desc[1])
                    #img_desc['filename'] = caption, scale, physical unit, offset
                    img_desc[file_desc[0]] = file_desc[1:]

                #if true, file describes spectrogram (ie hyperspectral image)
                if sline[0].startswith('FileDesc2Begin'):

                    no_descriptors = 10
                    file_desc = []

                    for i  in range(no_descriptors):
                        line_desc = [val.strip() for val in lines[index+i+1].split(':')]
                        file_desc.append(line_desc[1])
                    #caption, bytes perpixel, scale, physical unit, offset, offset, datatype, bytes per reading
                    #filename wavelengths, phys units wavelengths.
                    spectrogram_desc[file_desc[0]] = file_desc[1:]

                if sline[0].startswith('AFMSpectrumDescBegin'):

                    file_desc = []
                    line_desc = [val.strip() for val in lines[index+1].split(':')][1]

                    if 'powerspectrum' in line_desc:
                        no_descriptors = 2

                        for i in range(no_descriptors):

                            line_desc = [val.strip() for val in lines[index+i+1].split(':')]
                            file_desc.append(line_desc[1])
                        #file name, position x, position y
                        pspectrum_desc[file_desc[0]] = file_desc[1:]

                    else:

                        no_descriptors = 7
                        for i in range(no_descriptors):
                            line_desc = [val.strip() for val in lines[index+i+1].split(':')]
                            file_desc.append(line_desc[1])
                        #file name, position x, position y
                        spectrum_desc[file_desc[0]] = file_desc[1:]
            f.close()
            
        self.img_desc = img_desc
        self.spectrogram_desc = spectrogram_desc
        self.spectrum_desc = spectrum_desc
        self.pspectrum_desc = pspectrum_desc
        
    def read_spectrograms(self):
        """reads spectrograms, associated spectral values, and saves them in two dictionaries"""
        
        spectrograms = {}
        spectrogram_spec_vals = {}
        
        for file_name, descriptors in self.spectrogram_desc.items():

            spec_vals_i = np.loadtxt(os.path.join(self.directory, file_name.strip('.int') + 'Wavelengths.txt'))
            #if true, data is acquired with polarizer, with an attenuation data column
         
            if np.array(spec_vals_i).ndim == 2:
                spectrogram_spec_vals[file_name] = spec_vals_i[:, 0]
                attenuation = {}
                attenuation[file_name] = spec_vals_i[:, 1]
                self.attenuation = attenuation
            
            else:
                spectrogram_spec_vals[file_name] = spec_vals_i
                
            #load and save spectrograms
            spectrogram_i = np.fromfile(os.path.join(self.directory, file_name), dtype='i4')
            spectrograms[file_name] = np.zeros((self.x_len, self.y_len, len(spec_vals_i)))
            
            for y, line in enumerate(np.split(spectrogram_i, self.y_len)):

                for x, pt_spectrum in enumerate(np.split(line, self.x_len)):
                    spectrograms[file_name][x, y, :] = pt_spectrum * float(descriptors[2])

        self.spectrograms = spectrograms
        self.spectrogram_spec_vals = spectrogram_spec_vals

    def read_imgs(self):
        """reads images and saves to dictionary"""
        imgs = {}
        
        for file_name, descriptors in self.img_desc.items():

            img_i = np.fromfile(os.path.join(self.directory, file_name), dtype='i4')
            imgs[file_name] = np.zeros((self.x_len, self.y_len))
        
            for y, line in enumerate(np.split(img_i, self.y_len)):
            
                for x, pixel in enumerate(np.split(line, self.x_len)):
                    imgs[file_name][x, y] = pixel * float(descriptors[1])
        
        self.imgs = imgs

    def read_spectra(self):
        """reads all point spectra and saves to dictionary"""
        spectra = {}
        spectra_spec_vals = {}
        spectra_x_y_dim_name = {}
        
        for file_name, descriptors in self.spectrum_desc.items():
            spectrum_f = np.loadtxt(os.path.join(self.directory, file_name), skiprows=1)
            spectra_spec_vals[file_name] = spectrum_f[:, 0]
            spectra[file_name] = spectrum_f[:,1]
        
            with open(os.path.join(self.directory, file_name)) as f:
                spectra_x_y_dim_name[file_name]  = f.readline().strip('\n').split('\t')
        
        for file_name, descriptors in self.pspectrum_desc.items():
            spectrum_f = np.loadtxt(os.path.join(self.directory, file_name), skiprows=1)
            spectra_spec_vals[file_name] = spectrum_f[:, 0]
            spectra[file_name] = spectrum_f[:,1]
        
            with open(os.path.join(self.directory, file_name)) as f:
                spectra_x_y_dim_name[file_name]  = f.readline().strip('\n').split('\t')
        
        self.spectra = spectra
        self.spectra_spec_vals = spectra_spec_vals
        self.spectra_x_y_dim_name = spectra_x_y_dim_name

    def make_datasets(self):
        
        datasets = []
        self.make_dimensions()
 
        # Spectrograms
        if bool(self.spectrogram_desc):
           
           for spectrogram_f, descriptors in self.spectrogram_desc.items():

               # channel_i = create_indexed_group(self.h5_meas_grp, 'Channel_')
               spec_vals_i = self.spectrogram_spec_vals[spectrogram_f]
               
               spectrogram_data = self.spectrograms[spectrogram_f]
               dset = sid.Dataset.from_array(spectrogram_data, name=descriptors[0])
               dset.data_type = 'Spectrogram'
               dset.set_dimension(0, self.dim0)
               dset.set_dimension(1, self.dim0)

               # spectrogram_spec_dims = Dimension('Wavelength', descriptors[8], spec_vals_i)
               spectrogram_dims = Dimension(values=spec_vals_i, name='Spectrogram', 
                                            units=descriptors[3], quantity='Wavelength', type='spectral' )
               dset.set_dimension(2, spectrogram_dims)
               dset.metadata = {'Caption': descriptors[0],
                                'Bytes_Per_Pixel': descriptors[1],
                                'Scale': descriptors[2],
                                'Physical_Units': descriptors[3],
                                'Offset': descriptors[4],
                                'Datatype': descriptors[5],
                                'Bytes_Per_Reading': descriptors[6],
                                'Wavelength_File': descriptors[7],
                                'Wavelength_Units': descriptors[8]}
               
               datasets.append(dset)
               
        # Images
        if bool(self.img_desc):
            
            for img_f, descriptors in self.img_desc.items():
                
                img_data = self.imgs[img_f]
                dset = sid.Dataset.from_array(img_data, name = descriptors[0])
                dset.data_type = 'Image'
                dset.set_dimension(0, self.dim0)
                dset.set_dimension(1, self.dim1)   
                dset.units = descriptors[2]
                dset.quantity = descriptors[0]
                dset.metadata =  {'Caption': descriptors[0],
                                  'Scale': descriptors[1],
                                  'Physical_Units': descriptors[2],
                                  'Offset': descriptors[3]}

                datasets.append(dset)
                
        # Spectra
        if bool(self.spectrum_desc):
            
            for spec_f, descriptors in self.spectrum_desc.items():
                
                #create new measurement group for each spectrum
                x_name = self.spectra_x_y_dim_name[spec_f][0].split(' ')[0]
                x_unit = self.spectra_x_y_dim_name[spec_f][0].split(' ')[1]
                y_name = self.spectra_x_y_dim_name[spec_f][1].split(' ')[0]
                y_unit = self.spectra_x_y_dim_name[spec_f][1].split(' ')[1]
                dset = sid.Dataset.from_array(self.spectra[spec_f], name = 'Raw_Spectrum')

                dset.set_dimension(0, Dimension(np.array([float(descriptors[1])]), 
                                                name='X',units=self.params_dictionary['XPhysUnit'].replace('\xb5','u'),
                                                quantity = 'X_position'))
                
                dset.set_dimension(1, Dimension(np.array([float(descriptors[2])]), 
                                                name='Y',units=self.params_dictionary['YPhysUnit'].replace('\xb5','u'),
                                                quantity = 'Y_position'))
                dset.data_type = 'Spectrum'
                dset.units = y_unit
                dset.quantity = y_name
                spectra_dims = Dimension(values=self.spectra_spec_vals[spec_f], name='Wavelength', 
                                        units=x_unit, quantity=x_name, type='spectral' )
                dset.set_dimension(2, spectra_dims)
                dset.metadata = {'XLoc': descriptors[1], 'YLoc': descriptors[2]}

                datasets.append(dset)
        
        # Power Spectra
        if bool(self.pspectrum_desc):
            for spec_f, descriptors in self.pspectrum_desc.items():

                #create new measurement group for each spectrum
                x_name = self.spectra_x_y_dim_name[spec_f][0].split(' ')[0]
                x_unit = self.spectra_x_y_dim_name[spec_f][0].split(' ')[1]
                y_name = self.spectra_x_y_dim_name[spec_f][1].split(' ')[0]
                y_unit = self.spectra_x_y_dim_name[spec_f][1].split(' ')[1]
                dset = sid.Dataset.from_array(self.spectra[spec_f], name = 'Power_Spectrum')

                dset.set_dimension(0, Dimension(np.array([0]), 
                                                name='X',units=self.params_dictionary['XPhysUnit'].replace('\xb5','u'),
                                                quantity = 'X_position'))
                
                dset.set_dimension(1, Dimension(np.array([0]), 
                                                name='Y',units=self.params_dictionary['YPhysUnit'].replace('\xb5','u'),
                                                quantity = 'Y_position'))
                dset.data_type = 'Spectrum'
                dset.units = y_unit
                dset.quantity = y_name
                spectra_dims = Dimension(values=self.spectra_spec_vals[spec_f], name='Wavelength', 
                                        units=x_unit, quantity=x_name, type='spectral' )
                dset.set_dimension(2, spectra_dims)
                dset.metadata = {'XLoc': 0, 'YLoc': 0}
                datasets.append(dset)                

        return datasets

    def make_dimensions(self):
        x_range = float(self.params_dictionary['XScanRange'])
        y_range = float(self.params_dictionary['YScanRange'])
        x_center = float(self.params_dictionary['xCenter'])
        y_center = float(self.params_dictionary['yCenter'])

        x_start = x_center-(x_range/2); x_end = x_center+(x_range/2)
        y_start = y_center-(y_range/2); y_end = y_center+(y_range/2)

        dx = x_range/self.x_len
        dy = y_range/self.y_len
        
        #assumes y scan direction:down; scan angle: 0 deg
        y_linspace = -np.arange(y_start, y_end, step=dy)
        x_linspace = np.arange(x_start, x_end, step=dx)
        
        qtyx = self.params_dictionary['XPhysUnit'].replace('\xb5', 'u')
        qtyy = self.params_dictionary['YPhysUnit'].replace('\xb5', 'u')
        
        self.dim0 = Dimension(x_linspace, name = 'x', units = qtyx, 
                              dimension_type = 'spatial', quantity='Length')
        self.dim1 = Dimension(y_linspace, name = 'y', units = qtyy, 
                              dimension_type = 'spatial', quantity='Length')
        
        # self.pos_ind, self.pos_val, self.pos_dims = pos_ind, pos_val, pos_dims
        
        return 
        
    # HDF5 creation        
    def create_hdf5_file(self, append_path='', overwrite=False):
        """ Sets up the HDF5 file for writing 
        
        append_path : string (Optional)
            h5_file to add these data to, must be a path to the h5_file on disk
        overwrite : bool (optional, default=False)
            If True, will overwrite an existing .h5 file of the same name        
        """
        
        if not append_path:
            h5_path = os.path.join(self.directory, self.basename.replace('.txt', '.h5'))
            if os.path.exists(h5_path):
                if not overwrite:
                    raise FileExistsError('This file already exists). Set attribute overwrite to True')
                else:
                    print('Overwriting file', h5_path)
                    #os.remove(h5_path)
                    
            self.h5_f = h5py.File(h5_path, mode='w')

        else:
            if not os.path.exists(append_path):
                raise Exception('File does not exist. Check pathname.')
            self.h5_f = h5py.File(append_path, mode='r+')

        self.h5_img_grp = create_indexed_group(self.h5_f, "Images")
        self.h5_spectra_grp = create_indexed_group(self.h5_f, "Spectra")
        self.h5_spectrogram_grp = create_indexed_group(self.h5_f, "Spectrogram")
        
        write_simple_attrs(self.h5_img_grp, self.params_dictionary)
        write_simple_attrs(self.h5_spectra_grp, self.params_dictionary)
        write_simple_attrs(self.h5_spectrogram_grp, self.params_dictionary)
        
        return
    
    def write_datasets_hdf5(self):
        """ Writes the datasets as pyNSID datasets to the HDF5 file"""
        for dset in self.datasets:
            
            if 'IMAGE' in dset.data_type.name:
        
                write_nsid_dataset(dset, self.h5_img_grp)
        
            elif 'SPECTRUM' in dset.data_type.name:
        
                write_nsid_dataset(dset, self.h5_spectra_grp) 
                
            else:
                
                write_nsid_dataset(dset, self.h5_spectrogram_grp) 
    
        self.h5_f.file.close()    
    
        return