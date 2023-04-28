pywget
==================

command line wget downloader alternative, this can be module/package


Installing
------------

Install and update using `pip`_:

.. code-block:: text

    $ pip install pywget

pywget supports Python 2 and newer, Python 3 and newer, and PyPy.

.. _pip: https://pip.pypa.io/en/stable/quickstart/


Example
----------------

What does it look like? Here is an example of a simple pywget program:

.. code-block:: python

    from pywget import wget

    link = "http://www.test.com/test.tar.gz"
    wget.download(link, "/home/root/Downloads")


or run on terminal

.. code-block:: text

    $ python wget.py "http://www.test.com/test.tar.gz" -p /home/root/Downloads
    
Support
---------

*   Python 2.7 +, Python 3.x
*   Windows, Linux

Links
------

*   License: `BSD <https://bitbucket.org/licface/pywget/src/default/LICENSE.rst>`_
*   Code: https://bitbucket.org/licface/pywget
*   Issue tracker: https://bitbucket.org/licface/pywget/issues