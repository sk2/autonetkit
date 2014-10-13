#!/usr/bin/python
# -*- coding: utf-8 -*-

import itertools
from collections import namedtuple

import autonetkit.log as log
import networkx as nx
from ank_utils import unwrap_graph, unwrap_nodes
from autonetkit.anm import NmEdge, NmNode

# helper namedtuples - until have a more complete schema (such as from Yang)
static_route_v4 = namedtuple("static_route_v4",
                             ["prefix", "netmask", "nexthop", "metric"])

static_route_v6 = namedtuple("static_route_v6",
                             ["prefix", "nexthop", "metric"])


def sn_preflen_to_network(address, prefixlen):
    """Workaround for creating an IPNetwork from an address and a prefixlen
    TODO: check if this is part of netaddr module
    """

    import netaddr
    return netaddr.IPNetwork('%s/%s' % (address, prefixlen))


def fqdn(node):
    return '%s.%s' % (node.label, node.asn)


def name_folder_safe(foldername):
    for illegal_char in [' ', '/', '_', ',', '.', '&amp;', '-', '(', ')', ]:
        foldername = foldername.replace(illegal_char, '_')

    # Don't want double _

    while '__' in foldername:
        foldername = foldername.replace('__', '_')
    return foldername


def set_node_default(nm_graph, nbunch=None, **kwargs):
    """Sets all nodes in nbunch to value if key not already set
    Note: this won't apply to future nodes added
    """

    graph = unwrap_graph(nm_graph)
    if nbunch is None:
        nbunch = graph.nodes()
    else:
        nbunch = unwrap_nodes(nbunch)
    for node in nbunch:
        for (key, val) in kwargs.items():
            if key not in graph.node[node]:
                graph.node[node][key] = val


# TODO: also add ability to copy multiple attributes

# TODO: rename to copy_node_attr_from

def copy_attr_from(overlay_src, overlay_dst, src_attr, dst_attr=None,
                   nbunch=None, type=None, default=None):

    # TODO: add dest format, eg to convert to int

    if not dst_attr:
        dst_attr = src_attr

    graph_src = unwrap_graph(overlay_src)
    graph_dst = unwrap_graph(overlay_dst)
    if not nbunch:
        nbunch = graph_src.nodes()

    for node in nbunch:
        try:
            val = graph_src.node[node].get(src_attr, default)
        except KeyError:

            # TODO: check if because node doesn't exist in dest, or because
            # attribute doesn't exist in graph_src

            log.debug('Unable to copy node attribute %s for %s in %s'
                      % (src_attr, node, overlay_src))
        else:

            # TODO: use a dtype to take an int, float, etc

            if type is float:
                val = float(val)
            elif type is int:
                val = int(val)

            if node in graph_dst:
                graph_dst.node[node][dst_attr] = val


def copy_int_attr_from(overlay_src, overlay_dst, src_attr, dst_attr=None,
                       nbunch=None, type=None, default=None):

    # note; uses high-level API for practicality over raw speed

    if not dst_attr:
        dst_attr = src_attr

    if not nbunch:
        nbunch = overlay_src.nodes()

    for node in nbunch:
        for src_int in node:
            val = src_int.get(src_attr)
            if val is None:
                val = default

            if type is float:
                val = float(val)
            elif type is int:
                val = int(val)

            if node not in overlay_dst:
                continue

            dst_int = overlay_dst.interface(src_int)
            if dst_int is not None:
                dst_int.set(dst_attr, val)


def copy_edge_attr_from(overlay_src, overlay_dst, src_attr,
                        dst_attr=None, type=None, default=None):
    # note this won't work if merge/aggregate edges

    if not dst_attr:
        dst_attr = src_attr

    for edge in overlay_src.edges():
        try:
            val = edge.get(src_attr)
            if val is None:
                val = default
        except KeyError:

            # TODO: check if because edge doesn't exist in dest, or because
            # attribute doesn't exist in graph_src

            log.debug('Unable to copy edge attribute %s for (%s, %s) in %s'
                      % edge)
        else:

            # TODO: use a dtype to take an int, float, etc

            if type is float:
                val = float(val)
            elif type is int:
                val = int(val)

            try:
                overlay_dst.edge(edge).set(dst_attr, val)
            except AttributeError:
                # fail to debug - as attribute may not have been set
                log.debug('Unable to set edge attribute on %s in %s'
                          % (edge, overlay_dst))


# TODO: make edges own module

def wrap_edges(nm_graph, edges):
    """ wraps edge ids into edge overlay """

    # TODO: make support multigraphs

    edges = list(edges)
    if not any(len(e) for e in edges):
        return []  # each edge tuple is empty

    try:

        # strip out data from (src, dst, data) tuple

        edges = [(s, t) for (s, t, _) in edges]
    except ValueError:
        pass  # already of form (src, dst)

    return list(NmEdge(nm_graph._anm, nm_graph._overlay_id, src, dst)
                for (src, dst) in edges)


def wrap_nodes(nm_graph, nodes):
    """ wraps node id into node overlay """

    return (NmNode(nm_graph._anm, nm_graph._overlay_id, node)
            for node in nodes)


def in_edges(nm_graph, nodes=None):

    # TODO: make support multigraphs

    graph = unwrap_graph(nm_graph)
    edges = graph.in_edges(nodes)
    return wrap_edges(nm_graph, edges)


def split(nm_graph, edges, retain=None, id_prepend=''):

    if retain is None:
        retain = []

    try:
        # TODO: find more efficient operation to test if string-like
        retain.lower()
        retain = [retain]  # was a string, put into list
    except AttributeError:
        pass  # already a list

    graph = unwrap_graph(nm_graph)
    edges_to_add = []
    added_nodes = []
    edges = list(edges)

    for edge in edges:
        src = edge.src
        dst = edge.dst

        # Form ID for the new node

        if graph.is_directed():
            new_id = '%s%s_%s' % (id_prepend, src, dst)
        else:

            # undirected, make id deterministic across ank runs

            # use sorted for consistency
            (node_a, node_b) = sorted([src, dst])
            new_id = '%s%s_%s' % (id_prepend, node_a, node_b)

        if nm_graph.is_multigraph():
            new_id = new_id + '_%s' % edge.ekey

        ports = edge.raw_interfaces
        data = edge._data
        src_data = data.copy()
        if src in ports:
            src_int_id = ports[src.node_id]
            src_data['_ports'] = {src.node_id: src_int_id}
        dst_data = data.copy()
        if dst in ports:
            dst_int_id = ports[dst.node_id]
            dst_data['_ports'] = {dst.node_id: dst_int_id}

        # Note: don't retain ekey since adding to a new node

        append = (src.node_id, new_id, src_data)
        edges_to_add.append(append)
        append = (dst.node_id, new_id, dst_data)
        edges_to_add.append(append)

        added_nodes.append(new_id)

    nm_graph.add_nodes_from(added_nodes)
    nm_graph.add_edges_from(edges_to_add)

    # remove the pre-split edges

    nm_graph.remove_edges_from(edges)

    return wrap_nodes(nm_graph, added_nodes)


def explode_nodes(nm_graph, nodes, retain=None):
    """Explodes all nodes in nodes
    TODO: explain better
    TODO: Add support for digraph - check if nm_graph.is_directed()
    """
    if retain is None:
        retain = []

    log.debug('Exploding nodes')
    try:
        retain.lower()
        retain = [retain]  # was a string, put into list
    except AttributeError:
        pass  # already a list

    total_added_edges = []  # keep track to return

    for node in nodes:

        edges = node.edges()
        edge_pairs = [(e1, e2) for e1 in edges for e2 in edges if e1
                      != e2]
        added_pairs = set()
        for edge_pair in edge_pairs:
            (src_edge, dst_edge) = sorted(edge_pair)
            if (src_edge, dst_edge) in added_pairs:
                continue  # already added this link pair in other direction
            else:
                added_pairs.add((src_edge, dst_edge))

            src = src_edge.dst  # src is the exploded node
            dst = dst_edge.dst  # src is the exploded node

            if src == dst:
                continue  # don't add self-loop

            data = dict((key, src_edge._data.get(key)) for key in
                        retain)
            node_to_dst_data = dict((key, dst_edge._data.get(key))
                                    for key in retain)
            data.update(node_to_dst_data)

            data['_ports'] = {}
            try:
                src_int_id = src_edge.raw_interfaces[src.node_id]
            except KeyError:
                pass  # not set
            else:
                data['_ports'][src.node_id] = src_int_id

            try:
                dst_int_id = dst_edge.raw_interfaces[dst.node_id]
            except KeyError:
                pass  # not set
            else:
                data['_ports'][dst.node_id] = dst_int_id

            new_edge = (src.node_id, dst.node_id, data)

            # TODO: use add_edge

            nm_graph.add_edges_from([new_edge])
            total_added_edges.append(new_edge)

        nm_graph.remove_node(node)
    return wrap_edges(nm_graph, total_added_edges)


def label(nm_graph, nodes):
    return list(nm_graph._anm.node_label(node) for node in nodes)


def connected_subgraphs(nm_graph, nodes):
    nodes = list(unwrap_nodes(nodes))
    graph = unwrap_graph(nm_graph)
    subgraph = graph.subgraph(nodes)
    if not len(subgraph.edges()):

        # print "Nothing to aggregate for %s: no edges in subgraph"

        pass
    if graph.is_directed():
        component_nodes_list = \
            nx.strongly_connected_components(subgraph)
    else:
        component_nodes_list = nx.connected_components(subgraph)

    wrapped = []
    for component in component_nodes_list:
        wrapped.append(list(wrap_nodes(nm_graph, component)))

    return wrapped


def aggregate_nodes(nm_graph, nodes, retain=None):
    """Combines connected into a single node"""
    if retain is None:
        retain = []

    try:
        retain.lower()
        retain = [retain]  # was a string, put into list
    except AttributeError:
        pass  # already a list

    nodes = list(unwrap_nodes(nodes))
    graph = unwrap_graph(nm_graph)
    subgraph = graph.subgraph(nodes)
    if not len(subgraph.edges()):

        # print "Nothing to aggregate for %s: no edges in subgraph"

        pass
    total_added_edges = []
    if graph.is_directed():
        component_nodes_list = \
            nx.strongly_connected_components(subgraph)
    else:
        component_nodes_list = nx.connected_components(subgraph)
    for component_nodes in component_nodes_list:
        if len(component_nodes) > 1:
            component_nodes = [nm_graph.node(n)
                               for n in component_nodes]

            # TODO: could choose most connected, or most central?
            # TODO: refactor so use nodes_to_remove

            nodes_to_remove = list(component_nodes)
            base = nodes_to_remove.pop()  # choose a base device to retain
            log.debug('Retaining %s, removing %s' % (base,
                                                     nodes_to_remove))

            external_edges = []
            for node in nodes_to_remove:
                external_edges += [e for e in node.edges() if e.dst
                                   not in component_nodes]
                # all edges out of component

            log.debug('External edges %s' % external_edges)
            edges_to_add = []
            for edge in external_edges:
                dst = edge.dst
                data = dict((key, edge._data.get(key)) for key in
                            retain)
                ports = edge.raw_interfaces
                dst_int_id = ports[dst.node_id]

                # TODO: bind to (and maybe add) port on the new switch?

                data['_ports'] = {dst.node_id: dst_int_id}

                append = (base.node_id, dst.node_id, data)
                edges_to_add.append(append)

            nm_graph.add_edges_from(edges_to_add)
            total_added_edges += edges_to_add
            nm_graph.remove_nodes_from(nodes_to_remove)

    return wrap_edges(nm_graph, total_added_edges)


def most_frequent(iterable):
    """returns most frequent item in iterable"""

# from http://stackoverflow.com/q/1518522

    gby = itertools.groupby
    try:
        return max(gby(sorted(iterable)), key=lambda (x, v):
                   (len(list(v)), -iterable.index(x)))[0]
    except ValueError, error:
        log.warning('Unable to calculate most_frequent, %s' % error)
        return None


def neigh_most_frequent(nm_graph, node, attribute,
                        attribute_graph=None, allow_none=False):
    """Used to explicitly force most frequent -
    useful if integers such as ASN which would otherwise return mean"""

    # TODO: rename to median?

    graph = unwrap_graph(nm_graph)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph  # use input graph
    node = unwrap_nodes(node)
    values = [attribute_graph.node[n].get(attribute) for n in
              graph.neighbors(node)]
    values = sorted(values)
    if not allow_none:
        values = [v for v in values if v is not None]
    return most_frequent(values)


def neigh_average(nm_graph, node, attribute, attribute_graph=None):
    """
    averages out attribute from neighbors in specified nm_graph
    attribute_graph is the graph to read the attribute from
    if property is numeric, then return mean
    else return most frequently occuring value
    """

    graph = unwrap_graph(nm_graph)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph  # use input graph
    node = unwrap_nodes(node)
    values = [attribute_graph.node[n].get(attribute) for n in
              graph.neighbors(node)]

# TODO: use neigh_attr

    try:
        values = [float(val) for val in values]
        return sum(values) / len(values)
    except ValueError:
        return most_frequent(values)


def neigh_attr(nm_graph, node, attribute, attribute_graph=None):
    """TODO:
    tidy up parameters to take attribute_graph first, and
    then evaluate if attribute_graph set, if not then use attribute_graph
    as attribute
    explain how nm_graph and attribute_graph work, eg for G_ip and
    G_phy
    """

    graph = unwrap_graph(nm_graph)
    node = unwrap_nodes(node)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph  # use input graph

    # Only look at nodes which exist in attribute_graph

    neighs = (n for n in graph.neighbors(node))
    valid_nodes = (n for n in neighs if n in attribute_graph)
    return (attribute_graph.node[node].get(attribute) for node in
            valid_nodes)


def neigh_equal(nm_graph, node, attribute, attribute_graph=None):
    """Boolean, True if neighbors in nm_graph
    all have same attribute in attribute_graph"""

    neigh_attrs = neigh_attr(nm_graph, node, attribute, attribute_graph)
    return len(set(neigh_attrs)) == 1


def unique_attr(nm_graph, attribute):
    graph = unwrap_graph(nm_graph)
    return set(graph.node[node].get(attribute) for node in graph)


def groupby(attribute, nodes):
    """Takes a group of nodes and returns a generator of (attribute, nodes)
     for each attribute value A simple wrapped around itertools.groupby
     that creates a lambda for the attribute
    """

    keyfunc = lambda x: x.get(attribute)
    nodes = sorted(nodes, key=keyfunc)
    return itertools.groupby(nodes, key=keyfunc)


def boundary_nodes(graph, nodes):
    """ returns nodes at boundary of G based on
    edge_boundary from networkx """

    # TODO: move to utils
# TODO: use networkx boundary nodes directly: does the same thing

    graph = unwrap_graph(graph)
    nodes = list(nodes)
    nbunch = list(unwrap_nodes(nodes))

    # find boundary

    b_edges = nx.edge_boundary(graph, nbunch)  # boundary edges
    internal_nodes = [s for (s, _) in b_edges]
    assert all(n in nbunch for n in internal_nodes)  # check internal

    return wrap_nodes(graph, internal_nodes)
