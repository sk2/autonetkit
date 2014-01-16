"""
AutoNetkit Utilities
"""

#from anm import overlay_node, overlay_edge
import autonetkit

def call_log(fn, *args, **kwargs):
    def decorator(*args, **kwargs):
        #print "\t" + fn.__name__
        return fn(*args, **kwargs)

    return decorator

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

def merge_quagga_conf():
    # helper function to merge the quagga config files into a single file for
    # http://www.nongnu.org/quagga/docs/docs-multi/VTY-shell-integrated-configuration.html
    import pkg_resources
    import os
    import time

    templates_path =pkg_resources.resource_filename(__name__, "templates")
    zebra_dir = os.path.join(templates_path, "quagga", "etc", "zebra")
    #TODO: check the ordering - seems to matter
    conf_files = ["zebra.conf.mako", "bgpd.conf.mako", "ospfd.conf.mako", "isisd.conf.mako"]
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    data = ["##Merged by AutoNetkit merge_quagga_conf on %s" % timestamp]
    #TODO: replace newlines with !
    for conf_file in conf_files:
        filename = os.path.join(zebra_dir, conf_file)
        with open(filename) as fh:
            data.append(fh.read())

    ospfd_conf = os.path.join(templates_path, "quagga.conf.mako")
    with open(ospfd_conf, "w") as fh:
        fh.write("\n".join(data))

