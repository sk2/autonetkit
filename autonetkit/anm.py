#!/usr/bin/python
# -*- coding: utf-8 -*-
import functools
import itertools
import pprint
import string
import time
from functools import total_ordering

import autonetkit.log as log
import networkx as nx
from autonetkit.ank_utils import unwrap_edges, unwrap_nodes

try:
    import cPickle as pickle
except ImportError:
    import pickle

import logging


#TODO: rename duplicate use of logger var in log setup
class CustomAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return '[%s]: %s' % (self.extra['item'], msg), kwargs

class AutoNetkitException(Exception):

    pass




# TODO: rename to NmPort


