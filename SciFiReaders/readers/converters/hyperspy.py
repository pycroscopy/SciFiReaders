"""
Hyperspy dataset converter to sidpy
part of SciFiReader, a pycroscopy package

author: Gerd Duscher, UTK
First Version 11/19/2021
"""

import sidpy
import numpy as np

try:
    import hyperspy.api as hs
except ModuleNotFoundError:
    hs = None


def convert_hyperspy(s):
    """
    imports a hyperspy signal object into sidpy.Dataset

    Parameters
    ----------
    s: hyperspy dataset

    Return
    ------
    dataset: sidpy.Dataset
    """
    if not hs:
        raise ModuleNotFoundError("Hyperspy is not installed")
    if not isinstance(s, (hs.signals.Signal1D, hs.signals.Signal2D)):
        raise TypeError('This is not a hyperspy signal object')
    dataset = sidpy.Dataset.from_array(s, name=s.metadata.General.title)
    # Add dimension info
    axes = s.axes_manager.as_dictionary()

    if isinstance(s, hs.signals.Signal1D):
        if s.data.ndim < 2:
            dataset.data_type = 'spectrum'
        elif s.data.ndim > 1:
            if s.data.ndim == 2:
                dataset = sidpy.Dataset.from_array(np.expand_dims(s, 2), name=s.metadata.General.title)
                dataset.set_dimension(2, sidpy.Dimension([0], name='y', units='pixel',
                                      quantity='distance', dimension_type='spatial'))
            dataset.data_type = sidpy.DataType.SPECTRAL_IMAGE
        for key, axis in axes.items():
            if axis['navigate']:
                dimension_type = 'spatial'
            else:
                dimension_type = 'spectral'
            dim_array = np.arange(axis['size']) * axis['scale'] + axis['offset']
            if axis['units'] == '':
                axis['units'] = 'frame'
            dataset.set_dimension(int(key[-1]), sidpy.Dimension(dim_array, name=axis['name'], units=axis['units'],
                                                                quantity=axis['name'], dimension_type=dimension_type))

    elif isinstance(s, hs.signals.Signal2D):
        if s.data.ndim < 4:
            if s.data.ndim == 2:
                dataset.data_type = 'image'
            elif s.data.ndim == 3:
                dataset.data_type = 'image_stack'

            for key, axis in axes.items():
                if axis['navigate']:
                    dimension_type = 'temporal'
                else:
                    dimension_type = 'spatial'
                dim_array = np.arange(axis['size']) * axis['scale'] + axis['offset']
                if axis['units'] == '' or not isinstance(axis['units'], str):
                    axis['units'] = 'pixel'
                if not isinstance(axis['name'], str):
                    axis['name'] = str(key)

                dataset.set_dimension(int(key[-1]), sidpy.Dimension(dim_array, name=axis['name'], units=axis['units'],
                                                                    quantity=axis['name'],
                                                                    dimension_type=dimension_type))
        elif s.data.ndim == 4:
            dataset.data_type = 'IMAGE_4D'
            for key, axis in axes.items():
                if axis['navigate']:
                    dimension_type = 'spatial'
                else:
                    dimension_type = 'reciprocal'
                dim_array = np.arange(axis['size']) * axis['scale'] + axis['offset']
                if axis['units'] == '' or not isinstance(axis['units'], str):
                    axis['units'] = 'pixel'
                if not isinstance(axis['name'], str):
                    axis['name'] = str(key)
                dataset.set_dimension(int(key[-1]), sidpy.Dimension(dim_array, name=axis['name'], units=axis['units'],
                                                                    quantity=axis['name'],
                                                                    dimension_type=dimension_type))
    dataset.metadata = dict(s.metadata)
    dataset.original_metadata = dict(s.original_metadata)
    dataset.title = dataset.metadata['General']['title']
    if 'quantity' in dataset.metadata['Signal']:
        dataset.units = dataset.metadata['Signal']['quantity'].split('(')[-1][:-1]
        dataset.quantity = dataset.metadata['Signal']['quantity'].split('(')[0]
    dataset.source = 'hyperspy'
    return dataset
