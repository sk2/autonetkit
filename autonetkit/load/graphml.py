import networkx as nx
import string
import os
import itertools
import autonetkit.config
settings = autonetkit.config.settings
import autonetkit.log as log

def load_graphml(filename):
    #TODO: allow default properties to be passed in as dicts

    try:
        graph = nx.read_graphml(filename)
    except IOError:
        log.warning("Unable to read GraphML %s" % filename)
        return
    graph.graph['timestamp'] =  os.stat(filename).st_mtime

    # remove selfloops
    graph.remove_edges_from(edge for edge in graph.selfloop_edges())

    letters_single = (c for c in string.lowercase) # a, b, c, ... z
    letters_double = ("%s%s" % (a, b) for (a, b) in itertools.product(string.lowercase, string.lowercase)) # aa, ab, ... zz
    letters = itertools.chain(letters_single, letters_double) # a, b, c, .. z, aa, ab, ac, ... zz
#TODO: need to get set of current labels, and only return if not in this set

    #TODO: add cloud, host, etc
    # prefixes for unlabelled devices, ie router -> r_a
    label_prefixes = {
            'router': 'r',
            'switch': 'sw',
            'server': 'se',
            }

    current_labels = set(graph.node[node].get("label") for node in graph.nodes_iter())
    unique_label = (letter for letter in letters if letter not in current_labels)

#TODO: make sure device label set

# set our own defaults if not set
#TODO: store these in config file
    ank_node_defaults = {
            'asn': 1,
            'device_type': 'router'
            }
    node_defaults = graph.graph['node_default']
    for key, val in node_defaults.items():
        if val == "False":
            node_defaults[key] = False

    for key, val in ank_node_defaults.items():
        if key not in node_defaults or node_defaults[key] == "None":
            node_defaults[key] = val

    for node in graph:
        for key, val in node_defaults.items():
            if key not in graph.node[node]:
                graph.node[node][key] = val

    # and ensure asn is integer, x and y are floats
    for node in graph:
        graph.node[node]['asn'] = int(graph.node[node]['asn'])
        try:
            x = float(graph.node[node]['x'])
        except KeyError:
            x = 0
        graph.node[node]['x'] = x
        try:
            y = float(graph.node[node]['y'])
        except KeyError:
            y = 0
        graph.node[node]['y'] = y
        try:
            graph.node[node]['label']
        except KeyError:
            device_type = graph.node[node]['device_type']
            graph.node[node]['label'] = "%s_%s" % (label_prefixes[device_type], unique_label.next())

    ank_edge_defaults = {
            'type': 'physical',
            }
    edge_defaults = graph.graph['edge_default']
    for key, val in ank_edge_defaults.items():
        if key not in edge_defaults or edge_defaults[key] == "None":
            edge_defaults[key] = val

    for src, dst in graph.edges():
        for key, val in edge_defaults.items():
            if key not in graph[src][dst]:
                graph[src][dst][key] = val

    # allocate edge_ids
    for src, dst in graph.edges():
        graph[src][dst]['edge_id'] = "%s_%s" % (graph.node[src]['label'], graph.node[dst]['label'])

# apply defaults
# relabel nodes
#other handling... split this into seperate module!
# relabel based on label: assume unique by now!
    mapping = dict( (n, d['label']) for n, d in graph.nodes(data=True))
    if not all( key == val for key, val in mapping.items()):
        nx.relabel_nodes(graph, mapping, copy=False) # Networkx wipes data if remap with same labels
    return graph


