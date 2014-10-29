#!/usr/bin/python
# -*- coding: utf-8 -*-

import itertools
import logging

import autonetkit
import autonetkit.log as log
from autonetkit.anm.edge import NmEdge
from autonetkit.anm.graph_data import NmGraphData
from autonetkit.anm.interface import NmPort
from autonetkit.anm.node import NmNode
from autonetkit.exception import OverlayNotFound
# TODO: check if this is still a performance hit
from autonetkit.log import CustomAdapter

from autonetkit.anm.ank_element import AnkElement

class OverlayBase(AnkElement):

    '''Base class for overlays - overlay graphs, subgraphs, projections, etc'''

    def __init__(self, anm, overlay_id):
        """"""

        if overlay_id not in anm.overlay_nx_graphs:
            raise OverlayNotFound(overlay_id)

            # TODO: return False instead?

        self._overlay_id = overlay_id
        self._anm = anm
        logger = logging.getLogger('ANK')
        logstring = 'Overlay: %s' % str(overlay_id)
        logger = CustomAdapter(logger, {'item': logstring})
        object.__setattr__(self, 'log', logger)
        self.init_logging("graph")

    def __repr__(self):
        """

        Example:

        >>> anm = autonetkit.topos.house()
        >>> anm['phy']
        phy

        """

        return self._overlay_id

    def is_multigraph(self):
        """
        Example:

        >>> anm = autonetkit.topos.house()
        >>> anm['phy'].is_multigraph()
        False
        >>> anm = autonetkit.topos.multi_edge()
        >>> anm['phy'].is_multigraph()
        True

        """
        return self._graph.is_multigraph()

    @property
    def data(self):
        """Returns data stored on this overlay graph"""

        return NmGraphData(self._anm, self._overlay_id)

    def __contains__(self, n):
        """
        Example:

        >>> anm = autonetkit.topos.house()
        >>> "r1" in anm['phy']
        True
        >>> "test" in anm['phy']
        False
        """

        try:
            return n.node_id in self._graph
        except AttributeError:

            # try with node_id as a string

            return n in self._graph

    def interface(self, interface):
        """"""

        return NmPort(self._anm, self._overlay_id, interface.node_id,
                      interface.interface_id)

    def edge(self, edge_to_find, dst_to_find=None, key=0):
        '''returns edge in this graph with same src and dst
        and key for parallel edges (default is to return first edge)
        #TODO: explain parameter overloading: strings, edges, nodes...

        Example:

        >>> anm = autonetkit.topos.house()
        >>> g_phy = anm['phy']
        >>> e_r1_r2 = g_phy.edge("r1", "r2")

        Can also find from an edge

        >>> e_r1_r2_input = anm['input'].edge(e_r1_r2)

        And for multi-edge graphs can specify key

        >>> anm = autonetkit.topos.multi_edge()
        >>> e1 = anm['phy'].edge("r1", "r2", 0)
        >>> e2 = anm['phy'].edge("r1", "r2", 1)
        >>> e1 == e2
        False


        '''

        # TODO: handle multigraphs
        if isinstance(edge_to_find, NmEdge):
            # TODO: tidy this logic
            edge = edge_to_find  # alias for neater code
            if (edge.is_multigraph() and self.is_multigraph()
                and self._graph.has_edge(edge.src,
                                         edge.dst, key=edge.ekey)):
                return NmEdge(self._anm, self._overlay_id,
                              edge.src, edge.dst, edge.ekey)
            elif (self._graph.has_edge(edge.src, edge.dst)):
                return NmEdge(self._anm, self._overlay_id,
                              edge.src, edge.dst)

        if isinstance(edge_to_find, NmEdge):
            src_id = edge_to_find.src
            dst_id = edge_to_find.dst
            search_key = key

            if self.is_multigraph():
                for (src, dst, rkey) in self._graph.edges(src_id,
                                                          keys=True):
                    if dst == dst_id and rkey == search_key:
                        return NmEdge(self._anm, self._overlay_id, src,
                                      dst, search_key)

            for (src, dst) in self._graph.edges(src_id):
                if dst == dst_id:
                    return NmEdge(self._anm, self._overlay_id, src, dst)

        # TODO: tidy this logic up

        try:
            src = edge_to_find
            dst = dst_to_find
            src.lower()
            dst.lower()
            if self.is_multigraph():
                if self._graph.has_edge(src, dst, key=key):
                    return NmEdge(self._anm, self._overlay_id, src,
                                  dst, key)
            else:

                 # Single graph

                if self._graph.has_edge(src, dst):
                    return NmEdge(self._anm, self._overlay_id, src, dst)
        except AttributeError:
            pass  # not strings
        except TypeError:
            pass

        try:
            src_id = edge_to_find.node_id
            dst_id = dst_to_find.node_id
        except AttributeError:
            pass  # not nodes
        else:

            # TODO: combine duplicated logic from above

            search_key = key
            if self.is_multigraph():
                for (src, dst, rkey) in self._graph.edges(src_id,
                                                          keys=True):
                    if dst == dst_id and rkey == search_key:
                        return NmEdge(self._anm, self._overlay_id, src,
                                      dst, search_key)

            for (src, dst) in self._graph.edges(src_id):
                if dst == dst_id:
                    return NmEdge(self._anm, self._overlay_id, src, dst)

    def __getitem__(self, key):
        """"""

        return self.node(key)

    def node(self, key):
        """Returns node based on name
        This is currently O(N). Could use a lookup table

        Example:

        >>> anm = autonetkit.topos.house()
        >>> g_phy = anm['phy']
        >>> r1 = g_phy.node("r1")

        Can also find across layers
        >>> r1_input = anm['input'].node(r1)

        """

        # TODO: refactor

        try:
            if key.node_id in self._graph:
                return NmNode(self._anm, self._overlay_id, key.node_id)
        except AttributeError:

             # try as string id

            if key in self._graph:
                return NmNode(self._anm, self._overlay_id, key)

            # doesn't have node_id, likely a label string, search based on this
            # label

            for node in self:
                if str(node) == key:
                    return node
            # TODO: change warning to an exception
            log.warning('Unable to find node %s in %s ' % (key, self))
            return None

    def overlay(self, key):
        """Get to other overlay graphs in functions"""

        # TODO: refactor: shouldn't be returning concrete instantiation from
        # abstract parent!

        from autonetkit.anm.graph import NmGraph
        return NmGraph(self._anm, key)

    @property
    def name(self):
        """"""

        return self.__repr__()

    def __nonzero__(self):
        return self.anm.has_overlay(self._overlay_id)

    def node_label(self, node):
        """"""

        return repr(NmNode(self._anm, self._overlay_id, node))

    def has_edge(self, edge):
        """Tests if edge in graph"""

        if self.is_multigraph():
            return self._graph.has_edge(edge.src, edge.dst, edge.ekey)

        return self._graph.has_edge(edge.src, edge.dst)

    def __iter__(self):
        """"""

        return iter(self.nodes())

    def __len__(self):
        """"""

        return len(self._graph)

    def nodes(self, *args, **kwargs):
        """

        >>> anm = autonetkit.topos.multi_as()
        >>> g_phy = anm["phy"]
        >>> g_phy.nodes()
        [r4, r5, r6, r7, r1, r2, r3, r8, r9, r10]

        >>> g_phy.nodes(asn=1)
        [r4, r5, r1, r2, r3]

        >>> g_phy.nodes(asn=3)
        [r7, r8, r9, r10]

        >>> g_phy.nodes(asn=1, ibgp_role="RR")
        [r4, r5]

        >>> g_phy.nodes(asn=1, ibgp_role="RRC")
        [r1, r2, r3]

        """

        result = list(NmNode(self._anm, self._overlay_id, node)
                      for node in self._graph)

        if len(args) or len(kwargs):
            result = self.filter(result, *args, **kwargs)
        return result

    def routers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be router

        >>> anm = autonetkit.topos.mixed()
        >>> anm['phy'].routers()
        [r1, r2, r3]

        """

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_router()]

    def switches(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be switch

        >>> anm = autonetkit.topos.mixed()
        >>> anm['phy'].switches()
        [sw1]

        """

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_switch()]

    def servers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be server

        >>> anm = autonetkit.topos.mixed()
        >>> anm['phy'].servers()
        [s1]

        """

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_server()]

    def l3devices(self, *args, **kwargs):
        """Shortcut for nodes(), tests if device is_l3device

        >>> anm = autonetkit.topos.mixed()
        >>> anm['phy'].l3devices()
        [s1, r1, r2, r3]

        """

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_l3device()]

    def device(self, key):
        """To access programatically"""

        return NmNode(self._anm, self._overlay_id, key)

    def groupby(self, attribute, nodes=None):
        """Returns a dictionary sorted by attribute

        >>> anm = autonetkit.topos.house()
        >>> g_phy = anm['phy']
        >>> g_phy.groupby("asn")
        {1: [r1, r2, r3], 2: [r4, r5]}

        Can also specify a subset to work from

        >>> nodes = [n for n in g_phy if n.degree() > 2]
        >>> g_phy.groupby("asn", nodes=nodes)
        {1: [r2, r3]}

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

    def filter(self, nbunch=None, *args, **kwargs):
        """"""

        if nbunch is None:
            nbunch = self.nodes()

        def filter_func(node):
            """Filter based on args and kwargs"""

            return all(getattr(node, key) for key in args) \
                and all(getattr(node, key) == val for (key, val) in
                        kwargs.items())

        return [n for n in nbunch if filter_func(n)]

    def edges(self, src_nbunch=None, dst_nbunch=None, *args,
              **kwargs):
        """
        >>> anm = autonetkit.topos.house()
        >>> g_phy = anm['phy']
        >>> g_phy.edges()
        [phy: (r4, r5), phy: (r4, r2), phy: (r5, r3), phy: (r1, r2), phy: (r1, r3), phy: (r2, r3)]

        >>> g_phy.edge("r1", "r2").color = "red"
        >>> g_phy.edges(color = "red")
        [phy: (r1, r2)]

        """

# src_nbunch or dst_nbunch may be single node
# TODO: refactor this

        if src_nbunch:
            nbunch_out = []
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

        if self.is_multigraph():
            valid_edges = list((src, dst, key) for (src, dst, key) in
                               self._graph.edges(src_nbunch, keys=True))
        else:
            default_key = 0
            valid_edges = list((src, dst, default_key)
                               for (src, dst) in self._graph.edges(src_nbunch))

        if dst_nbunch:
            try:
                dst_nbunch = dst_nbunch.node_id
                dst_nbunch = set([dst_nbunch])
            except AttributeError:
                dst_nbunch = (n.node_id for n in dst_nbunch)
                dst_nbunch = set(dst_nbunch)

            valid_edges = list((src, dst, key) for (src, dst, key) in
                               valid_edges if dst in dst_nbunch)

        if len(args) or len(kwargs):
            all_edges = [NmEdge(self._anm, self._overlay_id, src, dst,
                                key) for (src, dst, key) in valid_edges]
            result = list(edge for edge in all_edges
                          if filter_func(edge))
        else:
            result = list(NmEdge(self._anm, self._overlay_id, src, dst,
                                 key) for (src, dst, key) in valid_edges)

        return list(result)

