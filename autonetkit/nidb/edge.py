import logging
from autonetkit.nidb.node import DmNode
from autonetkit.nidb.interface import DmInterface
from autonetkit.log import CustomAdapter
import autonetkit.log as log


class DmEdge(object):

    """API to access edge in nidb"""

    def __init__(self, nidb, src_id, dst_id, ekey=0):
        # Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)
        object.__setattr__(self, 'ekey', ekey)  # for multigraphs
        #logger = logging.getLogger("ANK")
        #logstring = "Edge: %s" % str(self)
        #self.log = CustomAdapter(logger, {'item': logstring})
        logger = log
        object.__setattr__(self, 'log', logger)

    def __repr__(self):
        if self.is_multigraph():
            return '(%s, %s, %s)' % (self.src,
                                     self.dst, self.ekey)

        return '(%s, %s)' % (self.src, self.dst)

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._ports

    @raw_interfaces.setter
    def raw_interfaces(self, value):
        self._ports = value

    def is_multigraph(self):
        return self._graph.is_multigraph()

    @property
    def src(self):
        return DmNode(self.nidb, self.src_id)

    @property
    def src_int(self):
        src_int_id = self._ports[self.src_id]
        return DmInterface(self.nidb, self.src_id, src_int_id)

    @property
    def dst_int(self):
        dst_int_id = self._ports[self.dst_id]
        return DmInterface(self.nidb, self.dst_id, dst_int_id)

    def __eq__(self, other):
        """"""
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
    def dst(self):
        return DmNode(self.nidb, self.dst_id)

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])

    def __nonzero__(self):
        """Allows for checking if edge exists
        """
        try:
            # TODO: refactor to be _graph.has_edge(src, dst)
            _ = self._graph[self.src_id][self.dst_id]
            return True
        except KeyError:
            return False

    @property
    def _data(self):
        """Return data the node belongs to"""
        if self.is_multigraph():
            return self._graph[self.src_id][self.dst_id][self.ekey]

        return self._graph[self.src_id][self.dst_id]

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.nidb.raw_graph()

    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)"""
        return self.__getattr__(key)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._data.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._data[key] = val
