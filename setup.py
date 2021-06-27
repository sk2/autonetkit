#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="autonetkit",
    version="0.12.3",
    description='Automatic configuration generation',
    long_description='Automatic configuration generation',

    entry_points={
        'console_scripts': [
            'autonetkit = autonetkit.console:main',
            'autonetkit_webserver = autonetkit.webserver.webserver:main',
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
        'Jinja2',
        'aiohttp',
        'aiohttp_jinja2',
        'requests',
        'pydantic'
    ],

    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
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
