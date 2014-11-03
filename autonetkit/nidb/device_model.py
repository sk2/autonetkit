import collections

import time

import networkx as nx

from autonetkit.nidb.edge import DmEdge
from autonetkit.nidb.node import DmNode
from autonetkit.nidb.base import DmBase


class DmGraphData(object):

    """API to access overlay graph data in network"""

    def __init__(self, nidb):
        # Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)

    def __repr__(self):
        return "DeviceModel data: %s" % self.nidb.raw_graph().graph

    def __getattr__(self, key):
        """Returns edge property"""
        return self.nidb.raw_graph().graph.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self.nidb.raw_graph().graph[key] = val

# TODO: make this inherit same overlay base as overlay_graph for add nodes etc properties
# but not the degree etc


class DmLabTopology(object):

    """API to access lab topology in network"""
    # TODO: replace this with ConfigStanza

    def __init__(self, nidb, topology_id):
        # Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'topology_id', topology_id)

    def __repr__(self):
        return "Lab Topology: %s" % self.topology_id

    @property
    def _topology_data(self):
        return self.nidb.raw_graph().graph['topologies'][self.topology_id]

    def dump(self):
        return str(self._topology_data)

    def __getattr__(self, key):
        """Returns topology property"""
        data = self._topology_data.get(key)
        return data

    def __setattr__(self, key, val):
        """Sets topology property"""
        self._topology_data[key] = val

    def set(self, key, val):
        """For consistency, topology.set(key, value) is neater
        than setattr(topology, key, value)"""
        return self.__setattr__(key, val)


class DeviceModel(DmBase):

    def __init__(self, network_model=None):
        super(DeviceModel, self).__init__()
        # only for connectivity, any other information stored on node
        if network_model and network_model['phy'].is_multigraph:
            self._graph = nx.MultiGraph()
        else:
            self._graph = nx.Graph()

        self._graph.graph['topologies'] = collections.defaultdict(dict)
        self._graph.graph['timestamp'] = time.strftime(
            "%Y%m%d_%H%M%S", time.localtime())

        if network_model:
            self._build_from_anm(network_model)

    def _build_from_anm(self, network_model):
        #TODO: Allow to specify which attributes to copy across
        #TODO: provide another function to copy across attributes post-creation
        g_phy = network_model['phy']
        g_graphics = network_model['graphics']
        self.add_nodes_from(g_phy, retain=['label', 'host', 'platform',
                                           'Network', 'update', 'asn', ])

        self.add_edges_from(g_phy.edges())
        self.copy_graphics(g_graphics)

    def topology(self, key):
        return DmLabTopology(self, key)

    def topologies(self):
        return iter(DmLabTopology(self, key)
                    for key in self._graph.graph['topologies'].keys())

    @property
    def timestamp(self):
        return self._graph.graph['timestamp']

    def subgraph(self, nbunch, name=None):
        nbunch = (n.node_id for n in nbunch)  # only store the id in overlay
        return DmSubgraph(self._graph.subgraph(nbunch), name)

    def boundary_nodes(self, nbunch, nbunch2=None):
        nbunch = (n.node_id for n in nbunch)  # only store the id in overlay
        return iter(DmNode(self, node)
                    for node in nx.node_boundary(self._graph,
                                                 nbunch, nbunch2))

    def boundary_edges(self, nbunch, nbunch2=None):
        nbunch = (n.node_id for n in nbunch)  # only store the id in overlay
        return iter(DmEdge(self, src, dst)
                    for (src, dst) in nx.edge_boundary(self._graph,
                                                       nbunch, nbunch2))


class DmSubgraph(DmBase):

    def __init__(self, graph, name=None):
        super(DmSubgraph, self).__init__()
        # TODO: need to refer back to the source nidb
        # only for connectivity, any other information stored on node
        self._graph = graph
        self._name = name

    def __repr__(self):
        return "nidb: %s" % self._name
