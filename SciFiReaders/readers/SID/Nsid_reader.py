# -*- coding: utf-8 -*-
"""
Reader capable of reading one or all NSID datasets present in a given HDF5 file

Created on Fri May 22 16:29:25 2020

@author: Gerd Duscher, Suhas Somnath, Maxim Ziadtinov
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

import h5py
import sidpy

try:
    from pyNSID.io.hdf_utils import check_if_main, get_all_main, \
        read_h5py_dataset
except ModuleNotFoundError:
    check_if_main = get_all_main = read_h5py_dataset = None


class NSIDReader(sidpy.Reader):

    def __init__(self, file_path):
        """
        Creates an instance of NSIDReader which can read one or more HDF5
        datasets formatted according to NSID into sidpy.Dataset objects

        Parameters
        ----------
        file_path : str, h5py.File, or h5py.Group
            Path to a HDF5 file or a handle to an open HDF5 file or group
            object

        Notes
        -----
        Please consider using the ``self._h5_file`` object to get handles to
        specific datasets or sub-trees that need to be read instead of opening
        the file again outside the context of this Reader.
        """
        super(NSIDReader, self).__init__(file_path)

        if not check_if_main:
            raise ModuleNotFoundError('Please install pyNSID to use this Reader')

        # Let h5py raise an OS error if a non-HDF5 file was provided
        self._h5_file = h5py.File(file_path, mode='r+')

        self._main_dsets = get_all_main(self._h5_file, verbose=False)

        # DO NOT close HDF5 file. Dask array will fail if you do so.

    def can_read(self):
        """
        Checks whether or not this Reader can read the provided file

        Returns
        -------
        bool :
            True if this Reader can read the provided file and if this file
            contains at least one NSID-formatted main dataset. Else, False
        """
        return len(self._main_dsets) > 0

    def read(self, h5_object=None):
        """
        Reads all available NSID main datasets or the specified h5_object

        Parameters
        ----------
        h5_object : h5py.Dataset or h5py.Group
            HDF5 Dataset to read or the HDF5 group under which to read all
            datasets

        Returns
        -------
        sidpy.Dataset or list of sidpy.Dataset objects
            Datasets present in the provided file
        """
        if h5_object is None:
            return self.read_all(recursive=True)
        if not isinstance(h5_object, (h5py.Group, h5py.Dataset)):
            raise TypeError('Provided h5_object was not a h5py.Dataset or '
                            'h5py.Group object but was of type: {}'
                            ''.format(type(h5_object)))
        self.__validate_obj_in_same_file(h5_object)
        if isinstance(h5_object, h5py.Dataset):
            return read_h5py_dataset(h5_object)
        else:
            return self.read_all(parent=h5_object)

    def __validate_obj_in_same_file(self, h5_object):
        """
        Internal function that ensures that the provided HDF5 object is within
        the same file as that provided in __init__

        Parameters
        ----------
        h5_object : h5py.Dataset, h5py.Group
            HDF5 object

        Raises
        ------
        OSError - if the provded object is in a different HDF5 file.
        """
        if h5_object.file != self._h5_file:
            raise OSError('The file containing the provided h5_object: {} is '
                          'not the same as provided HDF5 file when '
                          'instantiating this object: {}'
                          ''.format(h5_object.file.filename,
                                    self._h5_file.filename))

    def read_all(self, recursive=True, parent=None):
        """
        Reads all HDF5 datasets formatted according to NSID specifications.

        Parameters
        ----------
        recursive : bool, default = True
            We might just remove this kwarg
        parent : h5py.Group, Default = None
            HDF5 group under which to read all available datasets.
            By default, all datasets within the HDF5 file are read.

        Returns
        -------
        sidpy.Dataset or list of sidpy.Dataset objects
            Datasets present in the provided file
        """

        if parent is None:
            h5_group = self._h5_file
        else:
            if not isinstance(parent, h5py.Group):
                raise TypeError('parent should be a h5py.Group object')
            self.__validate_obj_in_same_file(parent)
            h5_group = parent

        if recursive:
            list_of_main = self._main_dsets
        else:
            list_of_main = []
            for key in h5_group:
                if isinstance(h5_group[key], h5py.Dataset):
                    if check_if_main(h5_group[key]):
                        list_of_main.append(h5_group[key])

        # Go through each of the identified
        list_of_datasets = []
        for dset in list_of_main:
            list_of_datasets.append(read_h5py_dataset(dset))
        return list_of_datasets

def close(self):
    self._h5_file.close()