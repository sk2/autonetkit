import networkx as nx
import string
import os
import itertools
import math
import autonetkit.config
settings = autonetkit.config.settings
import autonetkit.log as log
import autonetkit.exception
#TODO: fallback to python if cStringIO version is not available
from cStringIO import StringIO
from collections import defaultdict

def load_graphml(input_graph_string):
    #TODO: allow default properties to be passed in as dicts

    try:
        input_pseduo_fh = StringIO(input_graph_string) # load into filehandle to networkx
        graph = nx.read_graphml(input_pseduo_fh)
    except IOError:
        raise autonetkit.exception.AnkIncorrectFileFormat
    except IndexError:
        raise autonetkit.exception.AnkIncorrectFileFormat

    # remove selfloops
    graph.remove_edges_from(edge for edge in graph.selfloop_edges())
#TODO: if selfloops then log that are removing

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
    ank_graph_defaults = settings['Graphml']['Graph Defaults']
    for key, val in ank_graph_defaults.items():
        if key not in graph.graph:
            graph.graph[key] = val

    # handle yEd exported booleans: if a boolean is set, then only the nodes marked true have the attribute. need to map the remainder to be false to allow ANK logic 
    #for node in graph.nodes(data=True):
        #print node

    all_labels = dict((n, d.get('label')) for n, d in graph.nodes(data=True))
    label_counts = defaultdict(list)
    for (node, label) in all_labels.items():
        label_counts[label].append(node)

    # set default name for blank labels to ensure unique
    try:
        blank_labels = [v for k, v in label_counts.items() if not k].pop() # strip outer list
    except IndexError:
        blank_labels = [] # no blank labels
    for index, node in enumerate(blank_labels):
        #TODO: log message that no label set, so setting default
        graph.node[node]['label'] = "none___%s" % index

    duplicates = [(k, v) for k, v in label_counts.items() if k and len(v) > 1]
    for label, nodes in duplicates:
        for node in nodes:
            #TODO: need to check they don't all have same ASN... if so then warn
            graph.node[node]['label'] = "%s_%s" % (graph.node[node]['label'], graph.node[node]['asn'])

    boolean_attributes = set( k for n, d in graph.nodes(data=True)
            for k, v in d.items()
            if isinstance(v, bool)
            )

    for node in graph:
        for attr in boolean_attributes:
            if attr not in graph.node[node]:
                graph.node[node][attr] = False


#TODO: store these in config file
    ank_node_defaults = settings['Graphml']['Node Defaults']
    node_defaults = graph.graph['node_default'] # update with defaults from graphml
    for key, val in node_defaults.items():
        if val == "False":
            node_defaults[key] = False

    #TODO: do a dict update before applying so only need to iterate nodes once

    for key, val in ank_node_defaults.items():
        if key not in node_defaults or node_defaults[key] == "None":
            node_defaults[key] = val

    for node in graph:
        for key, val in node_defaults.items():
            if key not in graph.node[node]:
                graph.node[node][key] = val

    # map lat/lon from zoo to crude x/y approximation
    if graph.graph.get('Creator') == "Topology Zoo Toolset":
        all_lat = [graph.node[n].get('Latitude') for n in graph
                if graph.node[n].get("Latitude")]
        all_lon = [graph.node[n].get('Longitude') for n in graph
                if graph.node[n].get("Longitude")]

        lat_min = min(all_lat)
        lon_min = min(all_lon)
        lat_max = max(all_lat)
        lon_max = max(all_lon)
        lat_mean = (lat_max - lat_min) / 2
        lon_mean = (lon_max - lon_min) / 2
        lat_scale = 500/(lat_max - lat_min)
        lon_scale = 500/(lon_max - lon_min)
        for node in graph:
            lat = graph.node[node].get('Latitude') or lat_mean # set default to be mean of min/max
            lon = graph.node[node].get('Longitude') or lon_mean # set default to be mean of min/max
            graph.node[node]['y'] = -1 * lat * lat_scale
            graph.node[node]['x'] = lon * lon_scale

    if not( any(graph.node[n].get('x') for n in graph)
            and any(graph.node[n].get('y') for n in graph)):
# No x, y set, layout in a grid
        grid_length = int(math.ceil(math.sqrt(len(graph))))
        co_ords = [(x*100, y*100) for y in range(grid_length) for x in range(grid_length)]
        # (0,0), (100, 0), (200, 0), (0, 100), (100, 100) ....
        for node in sorted(graph):
            x, y = co_ords.pop(0)
            graph.node[node]['x'] = x
            graph.node[node]['y'] = y

    # and ensure asn is integer, x and y are floats
    for node in sorted(graph):
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

    ank_edge_defaults = settings['Graphml']['Edge Defaults']
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
    #if graph.graph.get("Network") == "European NRENs":
        #TODO: test if non-unique labels, if so then warn and proceed with this logic
        # we need to map node ids to contain network to ensure unique labels
        #mapping = dict( (n, "%s__%s" % (d['label'], d['asn'])) for n, d in graph.nodes(data=True))

    mapping = dict( (n, d['label']) for n, d in graph.nodes(data=True))
    if not all( key == val for key, val in mapping.items()):
        nx.relabel_nodes(graph, mapping, copy=False) # Networkx wipes data if remap with same labels

    return graph
