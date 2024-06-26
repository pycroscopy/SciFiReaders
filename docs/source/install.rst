Installation
============

Preparing for SciFiReaders
---------------------------
`SciFiReaders <https://github.com/pycroscopy/SciFiReaders>`_ requires many commonly used scientific and numeric python packages such as numpy, h5py etc.
To simplify the installation process, we recommend the installation of
`Anaconda <https://www.anaconda.com/distribution/>`_ which contains most of the prerequisite packages,
`conda <https://conda.io/docs/>`_ - a package / environment manager,
as well as an `interactive development environment <https://en.wikipedia.org/wiki/Integrated_development_environment>`_ - `Spyder <https://www.coursera.org/learn/python-programming-introduction/lecture/ywcuv/introduction-to-the-spyder-ide>`_.

Do you already have Anaconda installed?

- No?

  - `Download and install Anaconda <https://www.anaconda.com/download/>`_ for Python 3

- Yes?

  - Is your Anaconda based on python 3.6+?

    - No?

      - Uninstall existing Python / Anaconda distribution(s).
      - Restart computer
    - Yes?

      - Proceed to install SciFiReaders

Compatibility
~~~~~~~~~~~~~
* SciFiReaders is compatible with python 3.6 onwards. Please raise an issue if you find a bug.
* We do not support 32 bit architectures
* We only support text that is UTF-8 compliant due to restrictions posed by HDF5

Terminal
--------
Installing, uninstalling, or updating SciFiReaders (or any other python package for that matter) can be performed using the ``Terminal`` application.
You will need to open the Terminal to type any command shown on this page.
Here is how you can access the Terminal on your computer:

* Windows - Open ``Command Prompt`` by clicking on the Start button on the bottom left and typing ``cmd`` in the search box.
  You can either click on the ``Command Prompt`` that appears in the search result or just hit the Enter button on your keyboard.

  * Note - be sure to install in a location where you have write access.  Do not install as administrator unless you are required to do so.
* MacOS - Click on the ``Launchpad``. You will be presented a screen with a list of all your applications with a search box at the top.
  Alternatively, simultaneously hold down the ``Command`` and ``Space`` keys on the keyboard to launch the ``Spotlight search``.
  Type ``terminal`` in the search box and click on the ``Terminal`` application.
* Linux (e.g - Ubuntu) - Open the Dash by clicking the Ubuntu (or equivalent) icon in the upper-left, type "terminal".
  Select the Terminal application from the results that appear.

Installing SciFiReaders
-----------------------
1. Ensure that a compatible Anaconda distribution has been successfully installed
2. Open a `terminal <#terminal>`_ window.
3. Type the following commands into the terminal / command prompt and hit the Return / Enter key:

   .. code:: bash

      pip install SciFiReaders

Installing from a specific branch (advanced users **ONLY**)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Note that we do not recommend installing SciFiReaders this way since branches other than the master branch may contain bugs.

.. note::
   Windows users will need to install ``git`` before proceeding. Please type the following command in the Command Prompt:

   .. code:: bash

     conda install git

Install a specific branch of SciFiReaders (``dev`` in this case):

.. code:: bash

  pip install -U git+https://github.com/pycroscopy/SciFiReaders@dev


Updating SciFiReaders
---------------------

If you already have SciFiReaders installed and want to update to the latest version, use the following command in a terminal window:

.. code:: bash

   pip install -U --no-deps SciFiReaders

If it does not work try reinstalling the package:

.. code:: bash

   pip uninstall SciFiReaders
   pip install SciFiReaders
