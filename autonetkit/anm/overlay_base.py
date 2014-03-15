import itertools
import logging

import autonetkit.log as log
from autonetkit.anm.overlay_edge import OverlayEdge
from autonetkit.anm.overlay_graph_data import OverlayGraphData
from autonetkit.anm.overlay_interface import OverlayInterface
from autonetkit.anm.overlay_node import OverlayNode
from autonetkit.exception import OverlayNotFound
from autonetkit.log import CustomAdapter


class OverlayBase(object):

    '''Base class for overlays - overlay graphs, subgraphs, projections, etc'''

    def __init__(self, anm, overlay_id):
        """"""

        if overlay_id not in anm.overlay_nx_graphs:
            raise OverlayNotFound(overlay_id)
            #TODO: return False instead?
        self._anm = anm
        self._graph = None # implemented in inheritors
        self.anm = None # implemented in inheritors
        self._overlay_id = overlay_id
        logger = logging.getLogger("ANK")
        logstring = "Overlay: %s" % str(overlay_id)
        logger = CustomAdapter(logger, {'item': logstring})
        object.__setattr__(self, 'log', logger)

    def __repr__(self):
        """"""

        return self._overlay_id

    @property
    def data(self):
        """Returns data stored on this overlay graph"""

        return OverlayGraphData(self._anm, self._overlay_id)

    def __contains__(self, n):
        """"""

        try:
            return n.node_id in self._graph
        except AttributeError:

            # try with node_id as a string

            return n in self._graph

    def interface(self, interface):
        """"""

        return OverlayInterface(self._anm, self._overlay_id,
                                 interface.node_id,
                                 interface.interface_id)

    def edge(self, edge_to_find, dst_to_find=None):
        '''returns edge in this graph with same src and dst'''

        if isinstance(edge_to_find, OverlayEdge):
            src_id = edge_to_find.src
            dst_id = edge_to_find.dst

            # TODO: add MultiGraph support in terms of key here

            for (src, dst) in self._graph.edges_iter(src_id):
                if dst == dst_id:
                    return OverlayEdge(self._anm, self._overlay_id,
                                       src, dst)

        # TODO: tidy this logic up

        try:
            src = edge_to_find
            dst = dst_to_find
            src.lower()
            dst.lower()
            if self._graph.has_edge(src, dst):
                return OverlayEdge(self._anm, self._overlay_id, src,
                                   dst)
        except AttributeError:
            pass  # not strings
        except TypeError:
            pass

        try:
            if dst_to_find:
                src_id = edge_to_find.node_id
                search_id = dst_to_find.node_id
            else:
                log.warning("Searching by edge_id has been deprecated")
        except AttributeError:
            src_id = None
            search_id = edge_to_find

        for (src, dst) in self._graph.edges_iter(src_id):
            try:
                if (src, dst) == (src_id, search_id):

                    # searching by nodes

                    return OverlayEdge(self._anm, self._overlay_id,
                                       src, dst)
            except KeyError:
                pass  #

    def __getitem__(self, key):
        """"""

        return self.node(key)

    def node(self, key):
        """Returns node based on name
        This is currently O(N). Could use a lookup table"""

        try:
            if key.node_id in self._graph:
                return OverlayNode(self._anm, self._overlay_id,
                                   key.node_id)
        except AttributeError:

            # doesn't have node_id, likely a label string, search based on this
            # label

            for node in self:
                if str(node) == key:
                    return node
            log.warning('Unable to find node %s in %s ' % (key, self))
            return None

    def degree(self, node):
        """"""

        return node.degree()

    def neighbors(self, node):
        return iter(OverlayNode(self._anm, self._overlay_id, node)
                    for node in self._graph.neighbors(node.node_id))

    def overlay(self, key):
        """Get to other overlay graphs in functions"""

        #TODO: refactor: shouldn't be returning concrete instantiation from abstract parent!
        from overlay_graph import OverlayGraph
        return OverlayGraph(self._anm, key)

    @property
    def name(self):
        """"""

        return self.__repr__()

    def __nonzero__(self):
        return self.anm.has_overlay(self._overlay_id)

    def node_label(self, node):
        """"""

        return repr(OverlayNode(self._anm, self._overlay_id, node))

    def dump(self):
        """"""

        self._anm.dump_graph(self)

    def has_edge(self, edge):
        """Tests if edge in graph"""

        return self._graph.has_edge(edge.src, edge.dst)

    def __iter__(self):
        """"""

        return iter(OverlayNode(self._anm, self._overlay_id, node)
                    for node in self._graph)

    def __len__(self):
        """"""

        return len(self._graph)

    def nodes(self, *args, **kwargs):
        """"""

        result = self.__iter__()
        if len(args) or len(kwargs):
            result = self.filter(result, *args, **kwargs)
        return list(result)

    def routers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be router"""

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_router()]

    def switches(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be switch"""

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_switch()]

    def servers(self, *args, **kwargs):
            """Shortcut for nodes(), sets device_type to be server"""

            result = self.nodes(*args, **kwargs)
            return [r for r in result if r.is_server()]

    def l3devices(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be server"""
        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_l3device()]

    def device(self, key):
        """To access programatically"""

        return OverlayNode(self._anm, self._overlay_id, key)

    def groupby(self, attribute, nodes=None):
        """Returns a dictionary sorted by attribute

        >>> G_in.groupby("asn")
        {u'1': [r1, r2, r3, sw1], u'2': [r4]}
        """

        result = {}

        if not nodes:
            data = self.nodes()
        else:
            data = nodes
        data = sorted(data, key=lambda x: x.get(attribute))
        for (key, grouping) in itertools.groupby(data, key=lambda x:
                                                 x.get(attribute)):
            result[key] = list(grouping)

        return result

    def filter(
        self,
        nbunch=None,
        *args,
        **kwargs
    ):
        """"""

        if not nbunch:
            nbunch = self.nodes()

        def filter_func(node):
            """Filter based on args and kwargs"""

            return all(getattr(node, key) for key in args) \
                and all(getattr(node, key) == val for (key, val) in
                        kwargs.items())

        return (n for n in nbunch if filter_func(n))

    def edges(
        self,
        src_nbunch=None,
        dst_nbunch=None,
        *args,
        **kwargs
    ):
        """"""

# nbunch may be single node

        if src_nbunch:
            try:
                src_nbunch = src_nbunch.node_id
            except AttributeError:
                src_nbunch = (n.node_id for n in src_nbunch)

                              # only store the id in overlay

        def filter_func(edge):
            """Filter based on args and kwargs"""

            return all(getattr(edge, key) for key in args) \
                and all(getattr(edge, key) == val for (key, val) in
                        kwargs.items())

        valid_edges = ((src, dst) for (src, dst) in
                       self._graph.edges_iter(src_nbunch))
        if dst_nbunch:
            try:
                dst_nbunch = dst_nbunch.node_id
                dst_nbunch = set([dst_nbunch])
            except AttributeError:

                                 # faster membership test than other sequences

                dst_nbunch = (n.node_id for n in dst_nbunch)

                              # only store the id in OverlayEdge

                # faster membership test than other sequences
                dst_nbunch = set(dst_nbunch)

            valid_edges = ((src, dst) for (src, dst) in valid_edges
                           if dst in dst_nbunch)

        if len(args) or len(kwargs):
            all_edges = iter(OverlayEdge(self._anm, self._overlay_id,
                             src, dst) for (src, dst) in valid_edges)
            result = (edge for edge in all_edges if filter_func(edge))
        else:
            result = (OverlayEdge(self._anm, self._overlay_id, src,
                                  dst) for (src, dst) in valid_edges)
        return list(result)
