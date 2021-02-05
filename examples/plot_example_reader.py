"""
=================
Creating a Reader
=================

**Suhas Somnath**

8/28/2020

This document illustrates an example of extracting data out of proprietary raw
data files, thereby describing how one would write a ``sidpy.Reader`` class.

The captured information would be populated into a / set of ``sidpy.Dataset``
object(s) as appropriate.

Introduction
------------
In most scientific disciplines, commercial instruments tend to write the data and metadata out into proprietary file
formats that significantly impede access to the data and metadata, thwart sharing of data and correlation of data from
multiple instruments, and complicate long-term archival, among other things. One of the data wrangling steps in science
is the extraction of the data and metadata out of the proprietary file formats and writing the information into files
that are easier to access, share, etc. The overwhelming part of this data wrangling effort is in investigating how to
extract the data and metadata into memory. Often, the data and parameters in these files are **not** straightforward to
access. In certain cases, additional / dedicated software packages are necessary to access the data while in many other
cases, it is possible to extract the necessary information from built-in **numpy** or similar python packages included
with **anaconda**. Once the information is accessible in the computer memory, such as in the
form of numpy arrays, scientists have a wide variety of tools to write the data out into files.

Simpler data such as images or single spectra can easily be written into plain text files. Simple or complex / large /
multidimensional data can certainly be stored as numpy data files. However, there are significant drawbacks to writing
data into non-standardized structures or file formats. First, while the structure of the data and metadata may be
intuitive for the original author of the data, that may not be the case for another researcher. Furthermore, such
formatting may change from a day-to-day basis. As a consequence, it becomes challenging to develop code that can accept
such data whose format keeps changing.

One solution to these challenges is to write the data out into standardized files such as ``h5USID`` files.
The USID model aims to make data access, storage, curation, etc. simply by storing the data along with all
relevant parameters in a single file (HDF5 for now).

The process of copying data from the original format to **h5USID** files is called
**Translation** and the classes available in pyUSID and children packages such as pycroscopy that perform these
operation are called **Translators**.

As we alluded to earlier, the process of developing a ``sidpy.Reader`` can be
broken down into two basic components:

1. Extracting data and metadata out of the proprietary file format
2. Populating one or more ``sidpy.Dataset`` objects as necessary

This process is the same regardless of the origin, complexity, or size of the scientific data. It is not necessary that
the two components be disjoint - there are many situations where both components may need to happen simultaneously
especially when the data sizes are very large.

The goal of this document is to demonstrate how one would extract data and parameters from a Scanning Tunnelling
Spectroscopy (STS) raw data file obtained from an Omicron Scanning Tunneling Microscope (STM).
In this dataset, a spectra was collected for each position in a two-dimensional grid of spatial locations, thereby
resulting in a 3D dataset.

The code in this example is an abbreviation of the
`AscTranslator <https://github.com/pycroscopy/pycroscopy/blob/master/pycroscopy/io/translators/omicron_asc.py>`_
available in our sister package - `pycroscopy`.

Recommended pre-requisite reading
=================================

Before proceeding with this example, we recommend learning about ``Sidpy.Reader``:

.. tip::
    You can download and run this document as a Jupyter notebook using the link at the bottom of this page.

Import all necessary packages
=============================
There are a few setup procedures that need to be followed before any code is written. In this step, we simply load a
few python packages that will be necessary in the later steps.
"""

# Ensure python 3 compatibility:
from __future__ import division, print_function, absolute_import, unicode_literals

# The package for accessing files in directories, etc.:
import os
import zipfile

# Warning package in case something goes wrong
from warnings import warn
import subprocess
import sys


def install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])
# Package for downloading online files:
try:
    # This package is not part of anaconda and may need to be installed.
    import wget
except ImportError:
    warn('wget not found.  Will install with pip.')
    import pip
    install(wget)
    import wget

# The mathematical computation package:
import numpy as np

# The package used for creating and manipulating HDF5 files:
import h5py

# Packages for plotting:
import matplotlib.pyplot as plt

# import sidpy - supporting package for pyUSID:
try:
    import sidpy
except ImportError:
    warn('sidpy not found.  Will install with pip.')
    import pip
    install('sidpy')
    import sidpy

####################################################################################
# Procure the Raw Data file
# =========================
# Here we will download a compressed data file from Github and unpack it:

url = 'https://raw.githubusercontent.com/pycroscopy/pyUSID/master/data/STS.zip'
zip_path = 'STS.zip'
if os.path.exists(zip_path):
    os.remove(zip_path)
_ = wget.download(url, zip_path, bar=None)

zip_path = os.path.abspath(zip_path)
# figure out the folder to unzip the zip file to
folder_path, _ = os.path.split(zip_path)
zip_ref = zipfile.ZipFile(zip_path, 'r')
# unzip the file
zip_ref.extractall(folder_path)
zip_ref.close()
# delete the zip file
os.remove(zip_path)

data_file_path = 'STS.asc'

####################################################################################
# 1. Extracting data and metadata from proprietary files
# ------------------------------------------------------
# 1.1 Explore the raw data file
# =============================
#
# Inherently, one may not know how to read these ``.asc`` files. One option is to try and read the file as a text file
# one line at a time.
#
# If one is lucky, as in the case of these ``.asc`` files, the file can be read like conventional text files.
#
# Here is how we tested to see if the ``asc`` files could be interpreted as text files. Below, we read just the first 10
# lines in the file

with open(data_file_path, 'r') as file_handle:
    for lin_ind in range(10):
        print(file_handle.readline().replace('\n', ''))

####################################################################################
# 1.2 Read the contents of the file
# =================================
# Now that we know that these files are simple text files, we can manually go through the file to find out which lines
# are important, at what lines the data starts etc.
# Manual investigation of such ``.asc`` files revealed that these files are always formatted in the same way. Also, they
# contain instrument- and experiment-related parameters in the first ``403`` lines and then contain data which is
# arranged as one pixel per row.
#
# STS experiments result in 3 dimensional datasets ``(X, Y, current)``. In other words, a 1D array of current data (as a
# function of excitation bias) is sampled at every location on a two dimensional grid of points on the sample.
# By knowing where the parameters are located and how the data is structured, it is possible to extract the necessary
# information from these files.
#
# Since we know that the data sizes (<200 MB) are much smaller than the physical memory of most computers, we can start
# by safely loading the contents of the entire file to memory.

# Reading the entire file into memory
with open(data_file_path, 'r') as file_handle:
    string_lines = file_handle.readlines()

####################################################################################
# 1.3 Extract the metadata
# ========================
# In the case of these ``.asc`` files, the parameters are present in the first few lines of the file. Below we will
# demonstrate how we parse the first 17 lines to extract some very important parameters. Note that there are several
# other important parameters in the next 350 or so lines. However, in the interest of brevity, we will focus only on the
# first few lines of the file. The interested reader is recommended to read the ``ASCTranslator`` available in
# ``pycroscopy`` for more complete details.

# Preparing an empty dictionary to store the metadata / parameters as key-value pairs
parm_dict = dict()

# Reading parameters stored in the first few rows of the file
for line in string_lines[3:17]:
    # Remove the hash / pound symbol, if any
    line = line.replace('# ', '')
    # Remove new-line escape-character, if any
    line = line.replace('\n', '')
    # Break the line into two parts - the parameter name and the corresponding value
    temp = line.split('=')
    # Remove spaces in the value. Remember, the value is still a string and not a number
    test = temp[1].strip()
    # Now, attempt to convert the value to a number (floating point):
    try:
        test = float(test)
        # In certain cases, the number is actually an integer, check and convert if it is:
        if test % 1 == 0:
            test = int(test)
    except ValueError:
        pass
    parm_dict[temp[0].strip()] = test

# Print out the parameters extracted
for key in parm_dict.keys():
    print(key, ':\t', parm_dict[key])

####################################################################################
# At this point, we recommend reformatting the parameter names to standardized nomenclature.
# We realize that the materials imaging community has not yet agreed upon standardized nomenclature for metadata.
# Therefore, we leave this as an optional, yet recommended step.
# For example, in pycroscopy, we may categorize the number of rows and columns in an image under ``grid`` and
# data sampling parameters under ``IO``.
# As an example, we may rename ``x-pixels`` to ``positions_num_cols`` and ``y-pixels`` to ``positions_num_rows``.
#
# 1.4 Extract parameters that define dimensions
# =============================================
# Just having the metadata above and the main measurement data is insufficient to fully describe experimental data.
# We also need to know how the experimental parameters were varied to acquire the multidimensional dataset at hand.
# In other words, we need to answer how the grid of locations was defined and how the bias was varied to acquire the
# current information at each location. This is precisely what we will do below.
#
# Since, we did not parse the entire list of parameters present in the file above, we will need to make some up.
# Please refer to the formal ``ASCTranslator`` to see how this step would have been different.

num_rows = int(parm_dict['y-pixels'])
num_cols = int(parm_dict['x-pixels'])
num_pos = num_rows * num_cols
spectra_length = int(parm_dict['z-points'])

# We will assume that data was collected from -3 nm to +7 nm on the Y-axis or along the rows
y_vec = np.linspace(-3, 7, num_rows, endpoint=True)

# We will assume that data was collected from -5 nm to +5 nm on the X-axis or along the columns
x_vec = np.linspace(-5, 5, num_cols, endpoint=True)

# The bias was sampled from -1 to +1 V in the experiment. Here is how we generate the Bias axis:
bias_vec = np.linspace(-1, 1, spectra_length)

####################################################################################
# 1.5 Extract the data
# ====================
# We have observed that the data in these ``.asc`` files are consistently present after the first ``403`` lines of
# parameters. Using this knowledge, we need to populate a data array using data that is currently present as text lines
# in memory (from step 2).
#
# These ``.asc`` file store the 3D data (X, Y, spectra) as a 2D matrix (positions, spectra). In other words, the spectra
# are arranged one below another. Thus, reading the 2D matrix from top to bottom, the data arranged column-by-column,
# and then row-by-row So, for simplicity, we will prepare an empty 2D numpy array to store the data as it exists in the
# raw data file.
#
# Recall that in step 2, we were lucky enough to read the entire data file into memory given its small size.
# The data is already present in memory as a list of strings that need to be parsed as a matrix of numbers.

num_headers = 403

raw_data_2d = np.zeros(shape=(num_pos, spectra_length), dtype=np.float32)

# Iterate over ever measurement position:
for pos_index in range(num_pos):
    # First, get the correct (string) line corresponding to the current measurement position.
    # Recall that we would need to skip the many header lines to get to the data
    this_line = string_lines[num_headers + pos_index]
    # Each (string) line contains numbers separated by tabs (``\t``). Let us break the line into several shorter strings
    # each containing one number. We will ignore the last entry since it is empty.
    string_spectrum = this_line.split('\t')[:-1]  # omitting the new line
    # Now that we have a list of numbers represented as strings, we need to convert this list to a 1D numpy array
    # the converted array is set to the appropriate position in the main 2D array.
    raw_data_2d[pos_index] = np.array(string_spectrum, dtype=np.float32)

####################################################################################
# If the data is so large that it cannot fit into memory, we would need to read data one (or a few) position(s) at a
# time, process it (e.g. convert from string to numbers), and write it to the HDF5 file without keeping much or any data
# in memory.
#
# The three-dimensional dataset (``Y``, ``X``, ``Bias``) is currently represented as a two-dimensional array:
# (``X`` * ``Y``, ``Bias``). To make it easier for us to understand and visualize, we can turn it into a 3D array:

raw_data_3d = raw_data_2d.reshape(num_rows, num_cols, spectra_length)
print('Shape of 2D data: {}, Shape of 3D data: {}'.format(raw_data_2d.shape, raw_data_3d.shape))

####################################################################################
# Just as we did for the parameters (``X``, ``Y``, and ``Bias``) that were varied in the experiment,
# we need to specify the quantity that is recorded from the sensors / detectors, units, and what the data
# represents:

main_data_name = 'STS'
main_qty = 'Current'
main_units = 'nA'

####################################################################################
# Visualize the extracted data
# ============================
# Here is a visualization of the current-voltage spectra at a few locations:

fig, axes = sidpy.plot_utils.plot_curves(bias_vec, raw_data_2d, num_plots=9,
                                        x_label='bias (V)',
                                        y_label=main_qty + '(' + main_units + ')',
                                        title='Current-Voltage Spectra at different locations',
                                        fig_title_yoffset=1.05)

####################################################################################
# Here is a visualization of spatial maps at different bias values

fig, axes = sidpy.plot_utils.plot_map_stack(raw_data_3d, reverse_dims=True, pad_mult=(0.15, 0.15),
                                           title='Spatial maps of current at different bias', stdevs=2,
                                           color_bar_mode='single', num_ticks=3, x_vec=x_vec, y_vec=y_vec,
                                           evenly_spaced=True, fig_mult=(3, 3), title_yoffset=0.95)

for axis, bias_ind in zip(axes, np.linspace(0, len(bias_vec), 9, endpoint=False, dtype=np.uint)):
    axis.set_title('Bias = %3.2f V' % bias_vec[bias_ind])

####################################################################################
# 2. Populating the ``Dataset`` object
# ====================================
data_set = sidpy.Dataset.from_array(raw_data_3d, name='Raw_Data')
print(data_set)

####################################################################################
# Dimensions
data_set.set_dimension(0, sidpy.Dimension('y', y_vec,units='nm',
                                          quantity='Length',
                                          dimension_type='spatial'))
data_set.set_dimension(1, sidpy.Dimension('x', x_vec, units='nm',
                                          quantity='Length',
                                          dimension_type='spatial'))
data_set.set_dimension(2, sidpy.Dimension('bias', bias_vec,
                                          quantity='Bias',
                                          dimension_type='spectral'))

####################################################################################
# Generic top level metadata can be added as you go along
data_set.data_type = 'Current'
data_set.units = main_units
data_set.quantity = main_qty

####################################################################################
# Instrument-specific metadata
data_set.metadata = parm_dict

####################################################################################
# Print the dataset object
print(data_set)

####################################################################################
# Visualize the dataset object
data_set.plot()

####################################################################################
# How does one turn such ad-hoc code into a ``Reader`` class?

####################################################################################
# More information
# ================
# Our sister class - pycroscopy, has several
# `translators <https://github.com/pycroscopy/pycroscopy/tree/master/pycroscopy/io/translators>`_ that translate popular
# file formats generated by nanoscale imaging instruments.
# These will be moved to SciFiReaders soon
#
# We have found python packages online to open a few proprietary file formats and have written translators using these
# packages. If you are having trouble reading the data in your files and cannot find any packages online, consider
# contacting the manufacturer of the instrument which generated the data in the proprietary format for help.
#
# Cleaning up
# ===========
# Remove the original file:
os.remove(data_file_path)
