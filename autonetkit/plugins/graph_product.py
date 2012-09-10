import networkx as nx
import autonetkit.ank_utils as ank_utils
import autonetkit.ank as ank
import os
import pprint

def expand(G_in):
    """ Expands out graph products. G is the source "backbone" graph. H_x is the "PoP template" graphs
    """
    graph_unwrapped = ank_utils.unwrap_graph(G_in)
    G = graph_unwrapped.copy()
    print G.edges(data=True)
    
    ank.set_node_default(G_in, G_in, pop_template = "default")
    
    template_names = set(node.pop_template for node in G_in)
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
    for node in G_in:
        node.pop = node.label
        print node.pop

    # construct new graph
    G_out = nx.Graph() #TODO: what about bidirectional graphs?
    G_out.add_nodes_from(node_list(G, templates))
    print G_out.nodes()
# drop in replacement graph
    #remove_nodes = G_out.nodes()[3:]
    #print "remove_nodes", remove_nodes
    #G_out.remove_nodes_from(remove_nodes)
    print G_out.nodes()
    import itertools
    gen = itertools.count(10, 80)
    gen2 = itertools.count(10, 80)
    for node in G_out:
        G_out.node[node].update( {
            'x': gen.next(),
            'y': gen2.next() + 50,
            'asn': 1,
            'label': "%s_%s" % (node[1], node[0]),
            'device_type': "router",
            })

    
    # Update properties based on co-ordinates
    for node in G_out:
        u, v = node
        template = G.node[u]['pop_template']
        print u, v
        u_properties = G.node[u].copy()
        v_properties = dict(templates[template].node[v]) # create copy to append with
        x = float(u_properties.get('x')) + float(v_properties.get('x'))
        y = float(u_properties.get('y')) + float(v_properties.get('y'))
        u_properties.update(v_properties)
        u_properties['x'] = x
        u_properties['y'] = y
        u_properties['label'] = "%s_%s" % (v, u)
        u_properties['id'] = "%s_%s" % (v, u)
        #del properties['pop_template']
        print u_properties
        G_out.node[node] = u_properties

    edges = [(s, t, {'edge_id': gen.next(), 'type': 'physical'}) for s in G_out for t in G_out if s != t]
    edges = edges[:3]
    G_out.add_edges_from(edges)
    nx.relabel_nodes(G_out, dict( ((u, v), "%s_%s" % (v, u)) for (u, v) in G_out), copy = False)
    print G_out.edges(data=True)

    G_in._replace_graph(G_out)
    print list(G_in.edges())

    return



    nx.relabel_nodes(G_out, dict( ((u, v), "%s_%s" % (v, u)) for (u, v) in G_out), copy = False)
    pprint.pprint( graph_unwrapped.nodes(data=True))
    print "out"
    pprint.pprint( G_out.nodes(data=True))
    G_out.add_edge("r1_Melbourne", "r1_Sydney", edge_id = "a_b")
    print G_out.edges()
    graph_unwrapped.clear()
    G_in._replace_graph(G_out)
    print list(G_in.nodes())
    print list(G_in.edges())

#TODO: use "interpop" instead of "rooted"


def node_list(G, templates):
    # TODO: work out how to retain node attributes
    return [ (u,v) for u in G for v in templates[G.node[u]['pop_template']] ]



#TODO: What about edge ids?

