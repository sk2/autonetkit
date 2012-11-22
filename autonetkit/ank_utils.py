"""
AutoNetkit Utilities
"""

#from anm import overlay_node, overlay_edge
import autonetkit

def unwrap_nodes(nodes):
    """Unwrap nodes"""
    try:
        return nodes.node_id # treat as single node
    except AttributeError:
        return (node.node_id for node in nodes) # treat as list

def unwrap_edges(edges):
    """Unwrap edges"""
    return ( (edge.src_id, edge.dst_id) for edge in edges)

def unwrap_graph(overlay_graph):
    """Unwrap graph"""
    return overlay_graph._graph


def alphabetical_sort( l ): 
    """From http://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python"""
#TODO: fix as currently only handles strings - not objects with repr?
    import re 
    """ Sort the given iterable in the way that humans expect.""" 
    convert = lambda text: int(text) if text.isdigit() else text 
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)

def wrap_nodes(overlay_graph, nodes):
    """ wraps node id into node overlay """
#TODO: remove duplicate of this in ank.py
    return ( autonetkit.anm.overlay_node(overlay_graph._anm, overlay_graph._overlay_id, node)
            for node in nodes)
