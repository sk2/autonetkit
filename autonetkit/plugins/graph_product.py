import networkx as nx
import autonetkit.ank_utils as ank_utils
import autonetkit.ank as ank
import os
import pprint

def expand(G_phy):
    """ Expands out graph products. G is the source "backbone" graph. H_x is the "PoP template" graphs
    """
    graph_unwrapped = ank_utils.unwrap_graph(G_phy)
    G = graph_unwrapped.copy()
    
    ank.set_node_default(G_phy, G_phy, pop_template = "default")
    
    template_names = set(node.pop_template for node in G_phy)
# Load these templates
    templates = {}
    for template in template_names:
        template_filename = os.path.join("pop_templates", "%s.graphml" % template)
        pop_graph = nx.read_graphml(template_filename).to_undirected()
        nx.relabel_nodes(pop_graph, dict((n, data.get('label')) for n, data in pop_graph.nodes(data=True)), copy = False)
        templates[template] = pop_graph
    print templates
    for name, graph in templates.items():
        print graph.nodes(data=True)

# Set PoP based on label
    for node in G_phy:
        node.pop = node.label
        print node.pop

    # construct new graph
    G_out = nx.Graph() #TODO: what about bidirectional graphs?
    G_out.add_nodes_from(node_list(G, templates))
    print G_out.nodes()
# drop in replacement graph
    for node in G_out:
        G_out.node[node].update( {
            'x': 100,
            'y': 100,
            'asn': 1,
            'pop': "POP",
            'label': "%s_%s" % (node[1], node[0]),
            'device_type': "router",
            })

    nx.relabel_nodes(G_out, dict( ((u, v), "%s_%s" % (v, u)) for (u, v) in G_out), copy = False)
    pprint.pprint( graph_unwrapped.nodes(data=True))
    print "out"
    pprint.pprint( G_out.nodes(data=True))
    G_out.add_edge("r1_Melbourne", "r1_Sydney", edge_id = "a_b")
    print G_out.edges()
    graph_unwrapped.clear()
    G_phy._replace_graph(G_out)
    print list(G_phy.nodes())
    print list(G_phy.edges())

#TODO: use "interpop" instead of "rooted"


def node_list(G, templates):
    # TODO: work out how to retain node attributes
    return [ (u,v) for u in G for v in templates[G.node[u]['pop_template']] ]



#TODO: What about edge ids?

