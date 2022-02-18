# lines (164 sloc)  7.4 KB

"""
:class:`~ScopeReaders.generic.image.ImageTranslator` class that extracts the
data from typical image files into :class:`~sidpy.Dataset` objects
Created on Feb 9, 2016
@author: Mani Valleti
"""

import os
import sys

import numpy as np
import PIL
from sidpy import Dataset, Dimension, Reader

try:
    import tifffile as tff
except ModuleNotFoundError:
    tff = None


class ImageReader(Reader):
    """
    Translates data from an image file to a sidpy dataset
    """

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)
        image_path = self._parse_file_path(self._input_file_path)
        ext = os.path.splitext(image_path)[-1]
        if ext not in ['jpg', 'jpeg', 'png', 'bmp', '.tif', '.tiff']:
            raise NotImplementedError(
                'The provided file type {} is not supported by the reader as of now \n'.format(ext)
                + 'Please provide one of "jpg", "jpeg", "png", "bmp", ".tif", ".tiff" file types')

    @staticmethod
    def _parse_file_path(image_path):
        """
        Returns a list of all files in the directory given by path
        Parameters
        ---------------
        image_path : str
            absolute path to the image file
        Returns
        ----------
        image_path : str
            Absolute file path to the image
        """
        if not isinstance(image_path, str):
            raise TypeError("'image_path' argument for ImageReader should be a str")
        if not os.path.exists(os.path.abspath(image_path)):
            raise FileNotFoundError('Specified image does not exist.')
        else:
            image_path = os.path.abspath(image_path)

        return image_path

    def read(self, **image_args):
        """
        Translates the image in the provided file into a sidpy Dataset
        Parameters
        ----------------
        image_args : dict
            Arguments to be passed to read_image.  Arguments depend on the type of image.
        Returns
        ----------
        sidpy Dataset
        """

        image_path = self._parse_file_path(self._input_file_path)

        img_data, dimensions, metadata, original_metadata = read_image(image_path, **image_args)

        # Assuming that we have already dealt with classifying the shape
        # We are only as good as the tifffile package here

        # Working around occasional "cannot modify read-only array" error
        image = img_data.copy()

        data_set = Dataset.from_array(image, title='Image')

        data_set.data_type = 'image'
        # Can we somehow get the units and/or the quantity from the metadata??
        data_set.units = 'a. u.'
        data_set.quantity = 'Intensity'
        data_set.metadata = metadata.copy()
        data_set.original_metadata = original_metadata.copy()

        for i, dim in enumerate(dimensions):
            data_set.set_dimension(i, dim.copy())

        return data_set

    def can_read(self):
        """
        Tests whether or not the provided file has the appropriate extensions
        Returns
        -------

        """
        exts = ['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'csv', 'txt']
        return super(ImageReader, self).can_read(extension=exts)


def read_image(image_path, *args, **kwargs):
    """
    Read the image file at `image_path` into a numpy array either via numpy (.txt)
    or via tiffifle(.tif) or via pillow (.jpg, etc.)

    Parameters
    ----------
    image_path : str
        Path to the image file

    Returns
    -------
    image : :class:`numpy.ndarray`
        Array containing the image from the file `image_path`.
    """

    # As of now we are not trying to read any metadata from these image formats.
    # We will cross that bridge when someone raises an issue
    ext = os.path.splitext(image_path)[-1]
    original_metadata, metadata, dimensions = {}, {}, []
    if ext in ['jpg', 'jpeg', 'png', 'bmp']:
        img_data = np.asarray(PIL.Image.open(image_path))
        # Colored images, color channel last
        # Here we assume that the file path provided has a single image and not a stack
        # For stacks we turn our attention to tiff
        if len(img_data.shape) == 3:
            dimensions.append(Dimension(np.arange(img_data.shape[0]), 'y',
                                        units='generic', quantity='Length',
                                        dimension_type='spatial'))

            dimensions.append(Dimension(np.arange(img_data.shape[1]), 'x',
                                        units='generic', quantity='Length',
                                        dimension_type='spatial'))

            dimensions.append(Dimension(np.arange(img_data.shape[2]), 's',
                                        units='generic', quantity='SamplesPerPixel',
                                        dimension_type='frame'))
        # Grayscale single images
        if len(img_data.shape) == 2:
            dimensions.append(Dimension(np.arange(img_data.shape[0]), 'y',
                                        units='generic', quantity='Length',
                                        dimension_type='spatial'))

            dimensions.append(Dimension(np.arange(img_data.shape[1]), 'x',
                                        units='generic', quantity='Length',
                                        dimension_type='spatial'))

        return img_data, dimensions, metadata, original_metadata

    elif ext in ['.tif', '.tiff']:
        if tff is None:
            raise ModuleNotFoundError("tifffile is not installed")
        else:
            tif = tff.TiffFile(image_path)
            img_data = tif.asarray()

        # Only single series is supported for now, and for definition of a series refer the tifffile package
        img_shape, img_axes = tif.series[0].shape, tif.series[0].axes

        # Dealing with metadata that's common to the whole image, we will place this in original_metadata
        # First let's filter out all the attributes that end with metadata
        metadata_names = [a for a in dir(tif) if (not a.startswith('__') or not a.startswith('_'))
                          and a.endswith('_metadata')]
        for name in metadata_names:
            if getattr(tif, name) is not None:
                original_metadata[name] = getattr(tif, name)

        # Now metadata corresponding to individual frames. This is placed in metadata
        for page in tif.pages:
            for tag in page.tags:
                metadata[tag.name] = tag.value

        # Dealing with axes and dimensions
        # We will use the following dictionary to map tifffile axes to sidpy dimensions
        axes_dict = {'X': ['x', 'Length', 'spatial'],
                     'Y': ['y', 'Width', 'spatial'],
                     'Z': ['z', 'Depth', 'spatial'],
                     'S': ['s', 'SamplesPerPixel', 'frame'],
                     'T': ['t', 'Time', 'time'],
                     'C': ['c', 'Channel', 'frame'],
                     'Q': ['q', 'other', 'UNKNOWN']
                     }

        for i in range(len(img_shape)):
            if img_axes[i] == 'X' or img_axes[i] == 'Y':
                # We are here to handle X and Y dimensions
                # Here it is assumed that all the channels/time frames/depth frames have the same resolution unit

                res_name = 'XResolution' if img_axes[i] == 'X' else 'YResolution'
                for page in tif.pages:
                    if res_name in page.tags and 'ResolutionUnit' in page.tags:
                        if page.tags['ResolutionUnit'].value.value == 1:
                            # No unit provided
                            if isinstance(page.tags[res_name].value, tuple):
                                if page.tags[res_name].value == (1, 1):
                                    res, unit = 1, 'generic'
                                else:
                                    'It is assumed that the resolutions is given in pixels per inch'
                                    res, unit = page.tags[res_name].value[0], 'inches'
                            else:
                                if page.tags[res_name].value == 1:
                                    res, unit = 1, 'generic'
                                else:
                                    unit, res = 'inches', page.tags[res_name].value

                        elif page.tags['ResolutionUnit'].value.value == 2:
                            unit = 'inches'
                            if isinstance(page.tags[res_name].value, tuple):
                                res = page.tags[res_name].value[0]
                            else:
                                # At this point it is assumed that resolution is not a tuple but just and int/float
                                res = page.tags[res_name].value

                        elif page.tags['ResolutionUnit'].value.value == 3:
                            unit = 'cms'
                            if isinstance(page.tags[res_name].value, tuple):
                                res = page.tags[res_name].value[1]
                            else:
                                # At this point it is assumed that resolution is not a tuple but just and int/float
                                res = page.tags[res_name].value
                        break
                dimensions.append(Dimension(np.arange(img_shape[i]) * (1. / res), axes_dict[img_axes[i]][0],
                                            quantity=axes_dict[img_axes[i]][1], units=unit,
                                            dimension_type=axes_dict[img_axes[i]][2]))

            else:
                dimensions.append(Dimension(np.arange(img_shape[i]), axes_dict[img_axes[i]][0],
                                            quantity=axes_dict[img_axes[i]][1],
                                            dimension_type=axes_dict[img_axes[i]][2]))

        return img_data, dimensions, metadata, original_metadata
