#!/usr/bin/env python
from setuptools import setup

#from setuptools import setup, find_packages

setup (
     name = "autonetkit",
     version = "0.2.9",
     description = 'Automatic configuration generation for emulated networks',
     long_description = 'Automatic configuration generation for emulated networks',

     # simple to run 
     entry_points = {
         'console_scripts': [
             'autonetkit = autonetkit.console_script:main',
             'ank_webserver = autonetkit.webserver:main',
             'ank_measure_client = autonetkit.measure_client:main',
         ],
     },

     author = 'Simon Knight',
     author_email = "simon.knight@gmail.com",
     url = "http://www.autonetkit.org",
     packages = ['autonetkit', 'autonetkit.deploy',
     'autonetkit.load', 'autonetkit.plugins'],

     include_package_data = True, # include data from MANIFEST.in

     package_data = {'': ['settings.cfg', 'config/configspec.cfg', ]},
     download_url = ("http://pypi.python.org/pypi/AutoNetkit"),

     install_requires = ['netaddr', 'mako', 'networkx>=1.7', 
         'configobj', 'tornado', 
         #'textfsm', 'pika',
         # 'exscript==0.0.1'
         ],

     #Note: exscript disabled in default install: requires pycrypto which requires compilation (can cause installation issues)
     #dependency_links = [ 'https://github.com/knipknap/exscript/tarball/master#egg=exscript-0.0.1',],

     classifiers = [
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

