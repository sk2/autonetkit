import collections

import functools
import pprint
import string
import time
from functools import total_ordering

import autonetkit.ank_json
import autonetkit.log as log
import networkx as nx
from autonetkit.nidb.config_stanza import ConfigStanza

try:
    import cPickle as pickle
except ImportError:
    import pickle

from collections import OrderedDict
import logging
from autonetkit.ank_utils import call_log

from autonetkit.log import CustomAdapter

from autonetkit.nidb.interface import DmInterface
from autonetkit.nidb.edge import DmEdge
from autonetkit.nidb.node import DmNode
from autonetkit.nidb.base import DmBase

class DmGraphData(object):
    """API to access overlay graph data in network"""

    def __init__(self, nidb):
#Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)

    def __repr__(self):
        return "DevicesModel data: %s" % self.nidb._graph.graph

    def __getattr__(self, key):
        """Returns edge property"""
        return self.nidb._graph.graph.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self.nidb._graph.graph[key] = val

#TODO: make this inherit same overlay base as overlay_graph for add nodes etc properties
# but not the degree etc

class DmLabTopology(object):
    """API to access lab topology in network"""
    #TODO: replace this with ConfigStanza

    def __init__(self, nidb, topology_id):
#Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'topology_id', topology_id)

    def __repr__(self):
        return "Lab Topology: %s" % self.topology_id

    @property
    def _topology_data(self):
        return self.nidb._graph.graph['topologies'][self.topology_id]

    def dump(self):
        return str(self._topology_data)

    def __getattr__(self, key):
        """Returns topology property"""
        data = self._topology_data.get(key)
        return data

    def __setattr__(self, key, val):
        """Sets topology property"""
        self._topology_data[key] = val

class DevicesModel(DmBase):
    def __init__(self):
        self._graph = nx.Graph() # only for connectivity, any other information stored on node
        self._graph.graph['topologies'] = collections.defaultdict(dict)
        self._graph.graph['timestamp'] = time.strftime("%Y%m%d_%H%M%S", time.localtime())

    def topology(self, key):
        return DmLabTopology(self, key)

    def topologies(self):
        return iter(DmLabTopology(self.nidb, key) for key in self._graph.graph['topologies'].keys())

    @property
    def timestamp(self):
        return self._graph.graph['timestamp']

    def subgraph(self, nbunch, name = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return OverlaySubgraph(self._graph.subgraph(nbunch), name)

    def boundary_nodes(self, nbunch, nbunch2 = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return iter(DmNode(self, node)
                for node in nx.node_boundary(self._graph, nbunch, nbunch2))

    def boundary_edges(self, nbunch, nbunch2 = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return iter(DmEdge(self, src, dst)
                for (src, dst) in nx.edge_boundary(self._graph, nbunch, nbunch2))

class OverlaySubgraph(DmBase):
    def __init__(self, graph, name = None):
        #TODO: need to refer back to the source nidb
        self._graph = graph # only for connectivity, any other information stored on node
        self._name = name
    def __repr__(self):
        return "nidb: %s" % self._name
