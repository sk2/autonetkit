#!/usr/bin/env python
from setuptools import setup, find_packages
import sys

setup (
     name = "autonetkit",
     version = "0.5.21",
     description = 'Automatic configuration generation for emulated networks',
     long_description = 'Automatic configuration generation for emulated networks',

     # simple to run
     entry_points = {
         'console_scripts': [
             'autonetkit = autonetkit.console_script:console_entry',
             'ank_webserver = autonetkit.webserver:main',
             'ank_collect_server = autonetkit.collection.server:main',
         ],
     },

     author = 'Simon Knight',
     author_email = "simon.knight@gmail.com",
     url = "http://www.autonetkit.org",
     #packages = ['autonetkit', 'autonetkit.deploy', 'autonetkit.load', 'autonetkit.plugins'],

     packages=find_packages(exclude=('tests', 'docs')),

     include_package_data = True, # include data from MANIFEST.in

     #package_data = {'': ['settings.cfg', 'config/configspec.cfg', ]},
     download_url = ("http://pypi.python.org/pypi/autonetkit"),

     install_requires = [
         'netaddr==0.7.10',
         'mako==0.8.0',
         'networkx==1.7',
         'configobj==4.7.2',
         'tornado==3.0.1',
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


