import logging
from functools import total_ordering

from autonetkit.log import CustomAdapter
from autonetkit.anm.interface import NmPort
from autonetkit.anm.node import NmNode


@total_ordering
class NmEdge(object):

    """API to access link in network"""

    def __init__(
        self,
        anm,
        overlay_id,
        src_id,
        dst_id,
        ekey = 0,
    ):

        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)
        object.__setattr__(self, 'ekey', ekey) # for multigraphs
        logger = logging.getLogger("ANK")
        logstring = "Interface: %s" % str(self)
        logger = CustomAdapter(logger, {'item': logstring})
        object.__setattr__(self, 'log', logger)

    def __key(self):
        """Note: key doesn't include overlay_id to allow fast cross-layer comparisons"""

        # based on http://stackoverflow.com/q/2909106

        return (self.src_id, self.dst_id)

    def __hash__(self):
        """"""

        return hash(self.__key())

    def is_multigraph(self):
        return self._graph.is_multigraph()

    def __eq__(self, other):
        """"""
        #TODO: update for multigraph, also allow for comparison of multi to single,
        # and multi to two-tuple (src, dst) and three-tuple (src, dst, ekey)
        # do test if self, other are NmEdges or not...
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
            # self is single, other is single or multi -> only compare (src, dst)
            return (self.src_id, self.dst_id) == (other.src_id, other.dst_id)
        except AttributeError:
            #compare to strings
            return (self.src_id, self.dst_id) == other

    def __repr__(self):
        """String of node"""
        if self.is_multigraph():
            return '%s: (%s, %s, %s)' % (self.overlay_id, self.src,
                self.dst, self.ekey)

        return '%s: (%s, %s)' % (self.overlay_id, self.src, self.dst)

    def __getitem__(self, key):
        """"""

        from autonetkit.anm.graph import NmGraph
        overlay = NmGraph(self.anm, key)
        return overlay.edge(self)

    def __lt__(self, other):
        """"""
        if self.is_multigraph() and other.is_multigraph():
            return (self.src.node_id, self.dst.node_id, self.ekey) \
                < (other.src.node_id, other.dst.node_id, other.ekey)


        return (self.src.node_id, self.dst.node_id) \
            < (other.src.node_id, other.dst.node_id)

    # Internal properties
    def __nonzero__(self):
        """Allows for checking if edge exists
        """
        if self.is_multigraph():
            return self._graph.has_edge(self.src_id, self.dst_id,
                key=self.ekey)

        return self._graph.has_edge(self.src_id, self.dst_id)

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._interfaces

    @raw_interfaces.setter
    def raw_interfaces(self, value):
       self._interfaces = value

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
        """Source node of edge"""

        return NmNode(self.anm, self.overlay_id, self.src_id)

    @property
    def dst(self):
        """Destination node of edge"""

        return NmNode(self.anm, self.overlay_id, self.dst_id)


    # Interfaces

    def apply_to_interfaces(self, attribute):
        val = self.__getattr__(attribute)
        self.src_int.__setattr__(attribute, val)
        self.dst_int.__setattr__(attribute, val)

    @property
    def src_int(self):
        """Interface bound to source node of edge"""

        src_int_id = self._interfaces[self.src_id]
        return NmPort(self.anm, self.overlay_id,
                           self.src_id, src_int_id)

    @property
    def dst_int(self):
        """Interface bound to destination node of edge"""

        dst_int_id = self._interfaces[self.dst_id]
        return NmPort(self.anm, self.overlay_id,
                           self.dst_id, dst_int_id)

    def bind_interface(self, node, interface):
        """Bind this edge to specified index"""

        self._interfaces[node.id] = interface

    def interfaces(self):

        # TODO: warn if interface doesn't exist on node

        return iter(NmPort(self.anm, self.overlay_id,
                    node_id, interface_id) for (node_id,
                    interface_id) in self._interfaces.items())

    #

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])


    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)"""

        return self.__getattr__(key)

    def set(self, key, val):
        """For consistency, edge.set(key, value) is neater than
        setattr(edge, key, value)"""

        return self.__setattr__(key, val)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._data.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._data[key] = val
