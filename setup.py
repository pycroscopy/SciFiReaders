from codecs import open
import os
import setuptools

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

with open(os.path.join(here, 'SciFiReaders/__version__.py')) as f:
    __version__ = f.read().split("'")[1]

# TODO: Move requirements to requirements.txt
requirements = [  # basic
                'numpy',
                'toolz',  # dask installation failing without this
                'cytoolz',  # dask installation failing without this
                'dask>=2.20.0',
                'sidpy>=0.11.2',
                'numba==0.58; python_version < "3.11"',
                'numba>=0.59.0rc1; python_version >= "3.11"',
                'ipython>=7.1.0',
                'pyUSID',
                # generic:
                # Reader specific ones go to extras
               ]

setuptools.setup(
    name='SciFiReaders',
    version=__version__,
    description='Tools for extracting data and metadata from scientific data '
                'files',
    long_description=long_description,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering :: Information Analysis'],
    keywords=['imaging', 'spectra', 'multidimensional', 'scientific'],
    packages=setuptools.find_packages(exclude=["*.tests", "*.tests.*", "tests.*",
                                               "tests"]),
    url='https://pycroscopy.github.io/SciFiReaders/about.html',
    license='MIT',
    author='Pycroscopy contributors',
    author_email='pycroscopy@gmail.com',
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=['unitest', 'pytest', 'pywget', 'hyperspy', 'pyUSID', 'gwyfile'],
    platforms=['Linux', 'Mac OSX', 'Windows 11/10/8.1/8/7'],
    # package_data={'sample':['dataset_1.dat']}
    test_suite='unittest',
    # dependency='',
    # dependency_links=[''],
    include_package_data=True,
    # https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-dependencies
    extras_require={
        'hyperspy':  ["hyperspy"],
        'igor2': ["igor2"],
        "gwyddion": ["gwyfile"],
        'sid': ['pyUSID', 'pyNSID'],
        'image': ['pillow', 'tifffile']
    },
)
