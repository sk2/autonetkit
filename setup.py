#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="autonetkit",
    version="1.0.0",
    description='Automatic configuration generation',
    long_description='Automatic configuration generation',

    entry_points={
        'console_scripts': [
            'autonetkit = autonetkit.console_script:console_entry',
            'ank_webserver = autonetkit.webserver:main',
            'ank_collect_server = autonetkit.collection.server:main',
        ],
    },

    author='Simon Knight',
    author_email="simon.knight@gmail.com",
    url="http://www.autonetkit.org",

    packages=find_packages(exclude=('tests', 'docs')),

    include_package_data=True,  # include data from MANIFEST.in

    download_url=("http://pypi.python.org/pypi/autonetkit"),

    install_requires=[
        'netaddr',
        'networkx',
    ],

    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Networking",
        "Topic :: System :: Software Distribution",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],

)
