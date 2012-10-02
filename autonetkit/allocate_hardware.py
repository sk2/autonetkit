import networkx as nx
from ank_utils import unwrap_nodes, unwrap_graph, unwrap_edges

import random

#TODO: may need special handlers to access the interfaces.... add these into the ANM which accesses from the conn graph...

class HardwareModel(object):
    """Represents internals of a hardware device"""
    def __init__(self, graph):
        self.graph = graph

def allocate(anm):
    G_conn = anm['conn']
    G_phy = anm['phy']
    print "hardware"

    graph_conn = unwrap_graph(G_conn)
    graph_phy = unwrap_graph(G_phy)

    #graph_conn.add_node("aaa", x = 5, y = 10, label = "aa", asn = 1, device_type = "interface", device_sub_type = "aa")

#TODO: map this from distutils
    graph_internal = nx.read_graphml("autonetkit/hardware_profiles/netkit.graphml")

# normalize x/y for nodes
    min_x = min(float(graph_internal.node[n]['x']) for n in graph_internal)
    min_y = min(float(graph_internal.node[n]['y']) for n in graph_internal)
    print min_x, min_y
    for n in graph_internal:
        graph_internal.node[n]['x'] = float(graph_internal.node[n]['x']) - min_x
        graph_internal.node[n]['y'] = float(graph_internal.node[n]['y']) - min_y

    for n in graph_internal:
        print graph_internal.node[n]

# add at high level
    nodes = list(G_conn.nodes())
    for node_index, node in enumerate(G_phy):
        for subnode in graph_internal:
            #x = node.x + index*50
            #y = node.y + index*50
            x = float(node['graphics'].x) + graph_internal.node[subnode]['x'] /2
            y = float(node['graphics'].y) + graph_internal.node[subnode]['y']  /2
            #device =  str(node.label) + "a"
            #device = "a" + str(node.label).lower()
            #print node, 
            device = str(node.label) + str(node_index)
            label = "%s_%s" % (node.label, graph_internal.node[subnode]['label'])
            G_conn.add_node(label, x = x, y = y, asn = 1, label = device, device_type = "interface",
                    device_sub_type = None,  device = device 
                    )

        for src, dst in graph_internal.edges():
            src_label = "%s_%s" % (node.label, graph_internal.node[src]['label'])
            dst_label = "%s_%s" % (node.label, graph_internal.node[dst]['label'])
            edge_id = "%s_%s" % (src_label, dst_label)
#TODO: make add add_edge take raw ids 
            #G_conn.add_edge(src_label, dst_label, edge_id = edge_id)


#device = node.label)

    for node in nodes:
        G_conn.remove_node(node)

# now connect based on 
