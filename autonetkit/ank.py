import networkx as nx
from anm import overlay_node, overlay_edge
from collections import defaultdict
import itertools
import pprint
import autonetkit.log as log
from ank_utils import unwrap_nodes, unwrap_graph, unwrap_edges

try:
    import cPickle as pickle
except ImportError:
    import pickle

def fqdn(node):
    return "%s.%s" % (node.label, node.asn)

def name_folder_safe(foldername):
    for illegal_char in [" ", "/", "_", ",", ".", "&amp;", "-", "(", ")"]:
        foldername = foldername.replace(illegal_char, "_")
    # Don't want double _
    while "__" in foldername:
        foldername = foldername.replace("__", "_")
    return foldername

#TODO: have function that goes over a list, edge edges_to_add and sets edge_id if not set
#this cleans up the manual edge adding process

def set_node_default(overlay_graph, nbunch, **kwargs):
    """Sets all nodes in nbunch to value if key not already set"""
    graph = unwrap_graph(overlay_graph)
    nbunch = unwrap_nodes(nbunch)
    for node in nbunch:
        for key, val in kwargs.items():
            if key not in graph.node[node]:
                graph.node[node][key] = val


#TODO: also add ability to copy multiple attributes

#TODO: rename to copy_node_attr_from
def copy_attr_from(overlay_src, overlay_dst, src_attr, dst_attr = None, nbunch = None):
    #TODO: add dest format, eg to convert to int
    if not dst_attr:
        dst_attr = src_attr

    graph_src = unwrap_graph(overlay_src)
    graph_dst = unwrap_graph(overlay_dst)
    if not nbunch:
        nbunch = graph_src.nodes()

    for n in nbunch:
        try:
            graph_dst.node[n][dst_attr] = graph_src.node[n][src_attr]
        except KeyError:
            #TODO: check if because node doesn't exist in dest, or because attribute doesn't exist in graph_src
            log.debug("Unable to copy node attribute %s for %s in %s" % (src_attr, n, overlay_src))


def copy_edge_attr_from(overlay_src, overlay_dst, src_attr, dst_attr = None):
    graph_src = unwrap_graph(overlay_src)
    graph_dst = unwrap_graph(overlay_dst)
    if not dst_attr:
        dst_attr = src_attr

    for src, dst in graph_src.edges():
        try:
            graph_dst[src][dst][dst_attr] = graph_src[src][dst][src_attr]
        except KeyError:
            #TODO: check if because edge doesn't exist in dest, or because attribute doesn't exist in graph_src
            log.debug("Unable to copy edge attribute %s for (%s, %s) in %s" % (src_attr, src, dst, overlay_src))

def stringify_netaddr(graph):
    import netaddr
# converts netaddr from iterables to strings so can use with json
    replace_as_string = set([netaddr.ip.IPAddress, netaddr.ip.IPNetwork])
#TODO: see if should handle dict specially, eg expand to __ ?

    for key, val in graph.graph.items():
        if type(val) in replace_as_string:
            graph.graph[key] = str(val)

    for node, data in graph.nodes(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph.node[node][key] = str(val)

    for src, dst, data in graph.edges(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph[src][dst][key] = str(val)

    return graph

def save(overlay_graph):
    import netaddr
    graph = overlay_graph._graph.copy() # copy as want to annotate

# and put in basic attributes
    for node in overlay_graph:
        data = {}
        data['label'] = node.label
        #TODO: make these come from G_phy instead
        #graph.node[node.node_id]['label'] = node.overlay.input.label
        #graph.node[node.node_id]['device_type'] = node.overlay.input.device_type
        graph.node[node.node_id]['device_type'] = node.overlay.graphics.device_type
        graph.node[node.node_id]['x'] = node.overlay.graphics.x
        graph.node[node.node_id]['y'] = node.overlay.graphics.y

        graph.node[node.node_id].update(data)
#TODO: tidy this up

    replace_as_string = set([type(None), netaddr.ip.IPAddress, netaddr.ip.IPNetwork, dict, defaultdict])
#TODO: see if should handle dict specially, eg expand to __ ?

    for key, val in graph.graph.items():
        if type(val) in replace_as_string:
            graph.graph[key] = str(val)

    for node, data in graph.nodes(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph.node[node][key] = str(val)

    for src, dst, data in graph.edges(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph[src][dst][key] = str(val)

    mapping = dict( (n.node_id, str(n)) for n in overlay_graph) 
    nx.relabel_nodes( graph, mapping, copy=False)
#TODO: See why getting networkx.exception.NetworkXError: GraphML writer does not support <type 'NoneType'> as data values.
#TODO: process writer to allow writing of IPnetwork class values
    #filename = "%s.graphml" % overlay_graph.name
    #nx.write_graphml(graph, filename)

# probably want to create a graph from input with switches expanded to direct connections

#TODO: make edges own module
def wrap_edges(overlay_graph, edges):
    """ wraps edge ids into edge overlay """
    return ( overlay_edge(overlay_graph._anm, overlay_graph._overlay_id, src, dst)
            for src, dst in edges)

def wrap_nodes(overlay_graph, nodes):
    """ wraps node id into node overlay """
    return ( overlay_node(overlay_graph._anm, overlay_graph._overlay_id, node)
            for node in nodes)

def in_edges(overlay_graph, nodes=None):
    graph = unwrap_graph(overlay_graph)
    edges = graph.in_edges(nodes)
    return wrap_edges(overlay_graph, edges)

def split(overlay_graph, edges, retain = []):
    try:
        retain.lower() #TODO: find more efficient operation to test if string-like
        retain = [retain] # was a string, put into list
    except AttributeError:
        pass # already a list

    graph = unwrap_graph(overlay_graph)
    edges = list(unwrap_edges(edges))
    edges_to_add = []
    added_nodes = []
    for (src, dst) in edges:
        cd_id = "cd_%s_%s" % (src, dst)
        data = dict( (key, graph[src][dst][key]) for key in retain)
        edges_to_add.append( (src, cd_id, data))
        edges_to_add.append( (dst, cd_id, data))
        added_nodes.append(cd_id)

    graph.remove_edges_from(edges)
    graph.add_edges_from(edges_to_add)

    return wrap_nodes(overlay_graph, added_nodes)

def explode_nodes(overlay_graph, nodes, retain = []):
    """Explodes all nodes in nodes
    TODO: explain better
    TODO: Add support for digraph - check if overlay_graph.is_directed()
    """
    log.debug("Exploding nodes")
    try:
        retain.lower()
        retain = [retain] # was a string, put into list
    except AttributeError:
        pass # already a list

    graph = unwrap_graph(overlay_graph)
    nodes = unwrap_nodes(nodes)
    added_edges = []
#TODO: need to keep track of edge_ids here also?
    nodes = list(nodes)
    for node in nodes:
        log.debug("Exploding from %s" % node)
        neighbors = graph.neighbors(node)
        neigh_edge_pairs = ( (s,t) for s in neighbors for t in neighbors if s != t)
        edges_to_add = []
        for (src, dst) in neigh_edge_pairs:
            src_to_node_data = dict( (key, graph[src][node][key]) for key in retain)
            node_to_dst_data = dict( (key, graph[node][dst][key]) for key in retain)
            src_to_node_data.update(node_to_dst_data)
            edges_to_add.append((src, dst, src_to_node_data))

        graph.add_edges_from(edges_to_add)
        added_edges.append(edges_to_add)

        graph.remove_node(node)

    return wrap_edges(overlay_graph, added_edges)

def label(overlay_graph, nodes):
    return list(overlay_graph._anm.node_label(node) for node in nodes)

def aggregate_nodes(overlay_graph, nodes, retain = []):
    """Combines connected into a single node"""
    try:
        retain.lower()
        retain = [retain] # was a string, put into list
    except AttributeError:
        pass # already a list

    nodes = list(unwrap_nodes(nodes))
    graph = unwrap_graph(overlay_graph)
    subgraph = graph.subgraph(nodes)
    if not len(subgraph.edges()):
        #print "Nothing to aggregate for %s: no edges in subgraph"
        pass
    total_added_edges = []
    for component_nodes in nx.connected_components(subgraph):
        if len(component_nodes) > 1:
            base = component_nodes.pop() # choose one base device to retain
            nodes_to_remove = set(component_nodes) # remaining nodes, set for fast membership test
            external_edges = nx.edge_boundary(graph, component_nodes)
            edges_to_add = []
            for src, dst in external_edges:
                # src is the internal node to remove
                if src == base or dst == base:
                    continue # don't alter edges from base
                else:
                    if src in nodes_to_remove:
                        # edge from component to outside
                        data = dict( (key, graph[src][dst][key]) for key in retain)
                        edges_to_add.append((base, dst, data))
                    else:
                        # edge from outside into component
                        data = dict( (key, graph[dst][src][key]) for key in retain)
                        edges_to_add.append((base, src, data))
            graph.add_edges_from(edges_to_add)
            total_added_edges += edges_to_add
            graph.remove_nodes_from(nodes_to_remove)

    return wrap_edges(overlay_graph, total_added_edges)

# chain of two or more nodes

def most_frequent(iterable):
    """returns most frequent item in iterable"""
# from http://stackoverflow.com/q/1518522
    g = itertools.groupby
    return max(g(sorted(iterable)), key=lambda(x, v):(len(list(v)),-iterable.index(x)))[0]
    
def neigh_most_frequent(overlay_graph, node, attribute, attribute_graph = None):
    """Used to explicitly force most frequent - useful if integers such as ASN which would otherwise return mean"""
    graph = unwrap_graph(overlay_graph)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph # use input graph
    node = unwrap_nodes(node)
    values = [attribute_graph.node[n].get(attribute) for n in graph.neighbors(node)]
    return most_frequent(values)


def neigh_average(overlay_graph, node, attribute, attribute_graph = None):
    """ averages out attribute from neighbors in specified overlay_graph
    attribute_graph is the graph to read the attribute from
    if property is numeric, then return mean
        else return most frequently occuring value
    """
    graph = unwrap_graph(overlay_graph)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph # use input graph
    node = unwrap_nodes(node)
    values = [attribute_graph.node[n].get(attribute) for n in graph.neighbors(node)]
#TODO: use neigh_attr
    try:
        values = [float(val) for val in values]
        return sum(values)/len(values)
    except ValueError:
        return most_frequent(values)

def neigh_attr(overlay_graph, node, attribute, attribute_graph = None):
    #TODO: tidy up parameters to take attribute_graph first, and then evaluate if attribute_graph set, if not then use attribute_graph as attribute
#TODO: explain how overlay_graph and attribute_graph work, eg for G_ip and G_phy
    graph = unwrap_graph(overlay_graph)
    node = unwrap_nodes(node)
    if attribute_graph:
        attribute_graph = unwrap_graph(attribute_graph)
    else:
        attribute_graph = graph # use input graph

    #Only look at nodes which exist in attribute_graph
    neighs = (n for n in graph.neighbors(node))
    valid_nodes = (n for n in neighs if n in attribute_graph)
    return (attribute_graph.node[node].get(attribute) for node in valid_nodes)

def neigh_equal(overlay_graph, node, attribute, attribute_graph = None):
    """Boolean, True if neighbors in overlay_graph all have same attribute in attribute_graph"""
    neigh_attrs = neigh_attr(overlay_graph, node, attribute, attribute_graph)
    return len(set(neigh_attrs)) == 1

def unique_attr(overlay_graph, attribute):
    graph = unwrap_graph(overlay_graph)
    return set(graph.node[node].get(attribute) for node in graph)

def groupby(attribute, nodes):
    """Takes a group of nodes and returns a generator of (attribute, nodes) for each attribute value
    A simple wrapped around itertools.groupby that creates a lambda for the attribute
    """
    import itertools
    keyfunc = lambda x: x.get(attribute)
    nodes = sorted(nodes, key = keyfunc)
    return itertools.groupby(nodes, key = keyfunc)
