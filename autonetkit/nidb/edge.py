import logging
from autonetkit.nidb.node import DmNode
from autonetkit.log import CustomAdapter


class DmEdge(object):
    """API to access edge in nidb"""
    def __init__(self, nidb, src_id, dst_id):
#Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)
        logger = logging.getLogger("ANK")
        logstring = "Edge: %s" % str(self)
        self.log = CustomAdapter(logger, {'item': logstring})

    def __repr__(self):
        return "(%s, %s)" % (self.src, self.dst)

        return '(%s, %s)' % (self.src, self.dst)

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._ports

    @raw_interfaces.setter
    def raw_interfaces(self, value):
       self._ports = value

    def __setstate__(self, state):
        (nidb, src_id, dst_id) = state
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)

    @property
    def src(self):
        return DmNode(self.nidb, self.src_id)

    @property
    def dst(self):
        return DmNode(self.nidb, self.dst_id)

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])

    def __nonzero__(self):
        """Allows for checking if edge exists
        """
        try:
            #TODO: refactor to be _graph.has_edge(src, dst)
            _ = self._graph[self.src_id][self.dst_id]
            return True
        except KeyError:
            return False

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.nidb.raw_graph()

    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)"""
        return self.__getattr__(key)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._graph[self.src_id][self.dst_id].get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._graph[self.src_id][self.dst_id][key] = val
