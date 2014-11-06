import logging
from functools import total_ordering

import autonetkit
import autonetkit.log as log
from autonetkit.anm.interface import NmPort
from autonetkit.anm.node import NmNode
from autonetkit.log import CustomAdapter

from autonetkit.anm.ank_element import AnkElement

@total_ordering
class NmEdge(AnkElement):

    """API to access link in network"""

    def __init__(self, anm, overlay_id, src_id, dst_id, ekey=0):

        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)
        object.__setattr__(self, 'ekey', ekey)  # for multigraphs
        #logger = logging.getLogger("ANK")
        #logstring = "Interface: %s" % str(self)
        #logger = CustomAdapter(logger, {'item': logstring})
        logger = log
        object.__setattr__(self, 'log', logger)
        self.init_logging("edge")


    def __key(self):
        """Note: key doesn't include overlay_id to allow fast cross-layer comparisons"""

        # based on http://stackoverflow.com/q/2909106

        return (self.src_id, self.dst_id)

    def __hash__(self):
        """"""

        return hash(self.__key())

    def is_multigraph(self):
        return self._graph.is_multigraph()

    def is_parallel(self):
        """If there is more than one edge between the src, dst of this edge

        >>> anm = autonetkit.topos.multi_edge()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.is_parallel()
        True
        >>> edge = anm['phy'].edge("r2", "r3")
        >>> edge.is_parallel()
        False


        """
        # TODO: check this for digraph, multiidigraph
        return self._overlay().number_of_edges(self.src, self.dst) > 1

    def __eq__(self, other):
        """

        >>> anm = autonetkit.topos.house()
        >>> e1 = anm['phy'].edge("r1", "r2")
        >>> e2 = anm['phy'].edge("r1", "r2")
        >>> e1 == e2
        True

        Can also compare across layers
        >>> e2 = anm['input'].edge("r1", "r2")
        >>> e2
        input: (r1, r2)
        >>> e1 == e2
        True

        For multi-edge graphs can specify the key

        >>> anm = autonetkit.topos.multi_edge()
        >>> e1 = anm['phy'].edge("r1", "r2", 0)
        >>> e2 = anm['phy'].edge("r1", "r2", 1)
        >>> e1 == e2
        False

        #TODO: compare single-edge overlays to multi-edge


        """
        if self.is_multigraph():
            try:
                if other.is_multigraph():
                    return (self.src_id, self.dst_id, self.ekey) == (other.src_id,
                                                                     other.dst_id, other.ekey)
                else:
                    # multi, single
                    return (self.src_id, self.dst_id) == (other.src_id,
                                                          other.dst_id)

            except AttributeError:
                if len(other) == 2:
                    # (src, dst)
                    return (self.src_id, self.dst_id) == other
                elif len(other) == 3:
                    # (src, dst, key)
                    return (self.src_id, self.dst_id, self.ekey) == other

        try:
            # self is single, other is single or multi -> only compare (src,
            # dst)
            return (self.src_id, self.dst_id) == (other.src_id, other.dst_id)
        except AttributeError:
            # compare to strings
            return (self.src_id, self.dst_id) == other

    def __repr__(self):
        """String of node"""
        if self.is_multigraph():
            return '(%s, %s, %s)' % (self.src,
                                         self.dst, self.ekey)

        return '(%s, %s)' % (self.src, self.dst)

    def __getitem__(self, key):
        """"""

        from autonetkit.anm.graph import NmGraph
        overlay = NmGraph(self.anm, key)
        return overlay.edge(self)

    def _overlay(self):
        from autonetkit.anm import NmGraph
        return NmGraph(self.anm, self.overlay_id)

    def __lt__(self, other):
        """

        >>> anm = autonetkit.topos.house()
        >>> e1 = anm['phy'].edge("r1", "r2")
        >>> e2 = anm['phy'].edge("r1", "r3")
        >>> e1 < e2
        True
        >>> e2 < e1
        False

        """
        if self.is_multigraph() and other.is_multigraph():
            return (self.src.node_id, self.dst.node_id, self.ekey) \
                < (other.src.node_id, other.dst.node_id, other.ekey)

        return (self.src.node_id, self.dst.node_id) \
            < (other.src.node_id, other.dst.node_id)

    # Internal properties
    def __nonzero__(self):
        """Allows for checking if edge exists

        >>> anm = autonetkit.topos.house()
        >>> e1 = anm['phy'].edge("r1", "r2")
        >>> bool(e1)
        True

        For a non-existent link, will return False
        (NOTE: doesn't throw exception)
        >>> e2 = anm['phy'].edge("r1", "r5")
        >>> bool(e2)
        False



        """
        if self.is_multigraph():
            return self._graph.has_edge(self.src_id, self.dst_id,
                                        key=self.ekey)

        return self._graph.has_edge(self.src_id, self.dst_id)

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._ports

    @raw_interfaces.setter
    def raw_interfaces(self, value):
        self._ports = value

    @property
    def _graph(self):
        """Return graph the edge belongs to"""

        return self.anm.overlay_nx_graphs[self.overlay_id]

    @property
    def _data(self):
        """Return data the node belongs to"""
        if self.is_multigraph():
            return self._graph[self.src_id][self.dst_id][self.ekey]

        return self._graph[self.src_id][self.dst_id]

    # Nodes

    @property
    def src(self):
        """Source node of edge

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.src
        r1

        """

        return NmNode(self.anm, self.overlay_id, self.src_id)

    @property
    def dst(self):
        """Destination node of edge

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.dst
        r2

        """

        return NmNode(self.anm, self.overlay_id, self.dst_id)

    # Interfaces

    def apply_to_interfaces(self, attribute):
        """"

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.src_int.color = edge.dst_int.color = "blue"
        >>> (edge.src_int.color, edge.dst_int.color)
        ('blue', 'blue')
        >>> edge.color = "red"
        >>> edge.apply_to_interfaces("color")
        >>> (edge.src_int.color, edge.dst_int.color)
        ('red', 'red')
        """

        val = self.__getattr__(attribute)
        self.src_int.__setattr__(attribute, val)
        self.dst_int.__setattr__(attribute, val)

    @property
    def src_int(self):
        """Interface bound to source node of edge

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.src_int
        eth0.r1

        """

        src_int_id = self._ports[self.src_id]
        return NmPort(self.anm, self.overlay_id,
                      self.src_id, src_int_id)

    @property
    def dst_int(self):
        """Interface bound to destination node of edge

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.dst_int
        eth0.r2

        """

        dst_int_id = self._ports[self.dst_id]
        return NmPort(self.anm, self.overlay_id,
                      self.dst_id, dst_int_id)

    def bind_interface(self, node, interface):
        """Bind this edge to specified index"""

        self._ports[node.id] = interface

    def interfaces(self):
        """

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> list(edge.interfaces())
        [eth0.r1, eth0.r2]

        """

        # TODO: warn if interface doesn't exist on node

        return [NmPort(self.anm, self.overlay_id,
                       node_id, interface_id) for (node_id,
                                                   interface_id) in self._ports.items()]

    #

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])

    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.color = "red"
        >>> edge.get("color")
        'red'

        """

        return self.__getattr__(key)

    def set(self, key, val):
        """For consistency, edge.set(key, value) is neater than
        setattr(edge, key, value)

        >>> anm = autonetkit.topos.house()
        >>> edge = anm['phy'].edge("r1", "r2")
        >>> edge.color = "blue"
        >>> edge.color
        'blue'
        >>> edge.set("color", "red")
        >>> edge.color
        'red'


        """

        return self.__setattr__(key, val)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._data.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""

        if key == 'raw_interfaces':
            # TODO: fix workaround for
            # http://docs.python.org/2/reference/datamodel.html#customizing-attribute-access
            object.__setattr__(self, 'raw_interfaces', val)

        self._data[key] = val
