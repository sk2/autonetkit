"""
AutoNetkit Utilities
"""

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
