"""
AutoNetkit Utilities
"""

#from anm import overlay_node, overlay_edge
import autonetkit


def call_log(fn, *args, **kwargs):
    def decorator(*args, **kwargs):
        # print "\t" + fn.__name__
        return fn(*args, **kwargs)

    return decorator


def unwrap_nodes(nodes):
    """Unwrap nodes"""
    from autonetkit.anm import NmNode

    try:
        return nodes.node_id  # treat as single node
    except AttributeError:
        if isinstance(nodes, basestring):
            return nodes  # string

        return [node.node_id if isinstance(node, NmNode)
                else node
                for node in nodes]  # treat as list


def unwrap_edges(edges):
    """Unwrap edges"""
    retval = []
    for edge in edges:
        if edge.is_multigraph():
            retval.append((edge.src_id, edge.dst_id, edge.ekey))
        else:
            retval.append((edge.src_id, edge.dst_id))

    return retval


def unwrap_graph(nm_graph):
    """Unwrap graph"""
    return nm_graph._graph


def alphabetical_sort(l):
    """From http://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python"""
# TODO: fix as currently only handles strings - not objects with repr?
    import re
    """ Sort the given iterable in the way that humans expect."""
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def wrap_nodes(nm_graph, nodes):
    """ wraps node id into node overlay """
# TODO: remove duplicate of this in ank.py
    return (autonetkit.anm.overlay_node(nm_graph._anm, nm_graph._overlay_id, node)
            for node in nodes)


def merge_quagga_conf():
    # helper function to merge the quagga config files into a single file for
    # http://www.nongnu.org/quagga/docs/docs-multi/VTY-shell-integrated-configuration.html
    import pkg_resources
    import os
    import time

    templates_path = pkg_resources.resource_filename(__name__, "templates")
    zebra_dir = os.path.join(templates_path, "quagga", "etc", "zebra")
    # TODO: check the ordering - seems to matter
    conf_files = ["zebra.conf.mako", "bgpd.conf.mako",
                  "ospfd.conf.mako", "isisd.conf.mako"]
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    data = ["##Merged by AutoNetkit merge_quagga_conf on %s" % timestamp]
    # TODO: replace newlines with !
    for conf_file in conf_files:
        filename = os.path.join(zebra_dir, conf_file)
        with open(filename) as fh:
            data.append(fh.read())

    ospfd_conf = os.path.join(templates_path, "quagga.conf.mako")
    with open(ospfd_conf, "w") as fh:
        fh.write("\n".join(data))


"""Potential edge utils:
# TODO: see if these are still used
def attr_equal(self, *args):
   ""Return edges which both src and dst have attributes equal""

    return all(getattr(self.src, key) == getattr(self.dst, key)
               for key in args)

def attr_both(self, *args):
    ""Return edges which both src and dst have attributes set""

    return all(getattr(self.src, key) and getattr(self.dst, key)
               for key in args)

def attr_any(self, *args):
    ""Return edges which either src and dst have attributes set""

    return all(getattr(self.src, key) or getattr(self.dst, key)
               for key in args)
"""
