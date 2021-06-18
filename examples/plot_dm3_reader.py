"""
==============
Using a Reader
==============

**Gerd Duscher**

9/08/2020

This document illustrates an example of extracting data out of dm3
(Digital Micrograph) file.


Introduction
------------
Digital Micrograph from Gatan runs on many TEMs for data acquisition.
We read and plot such files here.

Import all necessary packages
=============================
There are a few setup procedures that need to be followed before any code is written. In this step, we simply load a
few python packages that will be necessary in the later steps.
"""

import sys
from sidpy.io.interface_utils import get_QT_app, openfile_dialog
sys.path.append('../')
from SciFiReaders import DM3Reader

####################################################################################
# Open a file dialog
# ===================
# Here we select the name of the file to open. We will be using the sidpy interface to do that.
# We start QT as a backend for the dialog first (in a notebook the magic command ``%gui qt5``)

app = get_QT_app()

# Then we can open QT file dialog to select a file

file_name = openfile_dialog()
#file_name = "C:/Users/gduscher/OneDrive - University of Tennessee/2020 Experiment/2020-09-20/10-EELS Acquire (dark ref corrected)CLDAl.dm3"

print(file_name)

# catch a bad selection or cancelling of file selection
if len(file_name) < 3 or file_name[-4:] != '.dm3':
    print('File not supported')
    exit()

####################################################################################

####################################################################################
# Read file
# =========
# We use the Reader to read the file into a sidpy dataset.
# All metadata (absolutely everything) is saved in the ``original_metadata`` attribute
# of the sidpy Dataset. If the selected file is not a dm3 File you get an ``IOError``.

dm3_reader = DM3Reader(file_name)
dataset = dm3_reader.read()

####################################################################################

###################################################################################
# Plot file
# ==========
# Only one command is necessary to plot the file.

dataset.plot()

####################################################################################
