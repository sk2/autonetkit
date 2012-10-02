import networkx as nx
from ank_utils import unwrap_nodes, unwrap_graph, unwrap_edges


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

    print graph_conn.nodes(data=True)
    print graph_phy.nodes(data=True)

# add at high level
    nodes = list(G_conn.nodes())
    for node in G_phy:
        for index in range(3):
            new_label = "%s_%s" % (node, index)
            #x = node.x + index*50
            #y = node.y + index*50
            x = y = 10
            G_conn.add_node(new_label, x = x, y = y, asn = 1, label = new_label, device_type = "interface",
                    device_sub_type = None,)

    for node in nodes:
        G_conn.remove_node(node)

    print "G conn nodes", [n for n in G_conn]

        




# now connect based on 
