import networkx as nx
import autonetkit.ank_utils as ank_utils
import autonetkit.ank as ank
import os
import pprint
import autonetkit.log as log
import autonetkit.load.graphml

def expand(G_in):
    """ Expands out graph products. G is the source "backbone" graph. H_x is the "PoP template" graphs
    """
    graph_unwrapped = ank_utils.unwrap_graph(G_in)
    G = graph_unwrapped.copy()
    
    ank.set_node_default(G_in, G_in)
    
    template_names = set(node.pop_template for node in G_in)
    template_names.discard("None")
    template_names.discard(None)
    if not len(template_names):
        log.debug("No PoP templates set")
        return # no templates set

# Load these templates
    templates = {}
    for template in template_names:
        template_filename = os.path.join("pop_templates", "%s.graphml" % template)
        try:
            pop_graph = autonetkit.load.graphml.load_graphml(template_filename) #TODO: pass in properties eg edge type = physical
        except Exception, e:
            log.warning("Unable to load pop template %s: %s" % (template, e))
            return
        pop_graph = pop_graph.to_undirected() # Undirected for now TODO: document this
        templates[template] = pop_graph

    # construct new graph
    G_out = nx.Graph() #TODO: what about bidirectional graphs?
    G_out.add_nodes_from(expand_nodes(G, templates))

    G_out.add_edges_from(intra_pop_links(G, templates))
    G_out.add_edges_from(inter_pop_links(G, templates))

    for s, t in G_out.edges():
        G_out[s][t]['type'] = 'physical' # ensure copied across
    
    # Update properties based on co-ordinates
    for node in G_out:
        u, v = node
        template = G.node[u]['pop_template']
        u_properties = dict(G.node[u])
        v_properties = dict(templates[template].node[v]) # create copy to append with
        x = float(u_properties.get('x')) + float(v_properties.get('x'))
        y = float(u_properties.get('y')) + float(v_properties.get('y'))
        asn = u_properties['asn']
        u_properties.update(v_properties)
        u_properties['x'] = x
        u_properties['y'] = y
        u_properties['label'] = "%s_%s" % (v, u)
        u_properties['id'] = "%s_%s" % (v, u)
        u_properties['pop'] = u
        u_properties['asn'] = asn # restore, don't inherit from pop
        del u_properties['pop_template']
        G_out.node[node] = u_properties

    nx.relabel_nodes(G_out, dict( ((u, v), "%s_%s" % (v, u)) for (u, v) in G_out), copy = False)
#TODO: set edge_ids
    for s, t in G_out.edges():
        G_out[s][t]['edge_id'] = "%s_%s" % (s, t)

    G_in._replace_graph(G_out)

    return

#TODO: use "interpop" instead of "rooted"


def expand_nodes(G, templates):
    # TODO: work out how to retain node attributes
    return [ (u,v) for u in G for v in templates[G.node[u]['pop_template']] ]

def intra_pop_links(G, templates):
    return [ ((u,v1), (u,v2)) for u in G for (v1, v2) in templates[G.node[u]['pop_template']].edges() ]


def inter_pop_links(G, templates, default_operator='cartesian'):
    #TODO:: list any edges without operator marked on them
# for brevity, Hx refers to templatex
    edges = []
    cartesian_operators = set(["cartesian", "strong"])
    tensor_operators = set(["tensor", "strong"])
    for (u1, u2) in G.edges():
        try:
            operator = G[u1][u2]['operator']
        except KeyError:
            operator =  default_operator

        if operator == "None": # from Graphml
            operator =  default_operator

        H1 = templates[G.node[u1]['pop_template']]
        H2 = templates[G.node[u2]['pop_template']]
# Node lists - if 'root' set then only use root nodes
        N1 = [n for n, d in H1.nodes(data=True) if 'interpop' in d and d['interpop']]
        if not len(N1):
            N1 = [n for n in H1] # no nodes marked interpop

        N2 = [n for n, d in H2.nodes(data=True) if 'interpop' in d and d['interpop']]
        if not len(N2):
            N2 = [n for n in H2] # no nodes marked interpop

        log.debug("Adding edges for (%s,%s) with operator %s" % (u1, u2, operator))

        log.debug("H nodes for u1 %s: %s" % ( G.node[u1]['pop_template'], ", ".join(str(N1))))
        log.debug("H nodes for u2 %s: %s" % ( G.node[u2]['pop_template'], ", ".join(str(N2))))
# 'root' not set
#TODO: fold rooted back into special case of cartesian - just do the same for now
        if operator == 'rooted':
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2
                    if H1.node[v1].get("interpop") == H2.node[v2].get("interpop") == True ]
            log.debug("Rooted product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

        if operator == 'lexical':
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2]
            log.debug("Lexical product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

        if operator in cartesian_operators:
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2 if v1 == v2]
            log.debug("Cartesian product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges
        if operator in tensor_operators:
            product_edges = [((u1, v1), (u2, v2)) for v1 in N1 for v2 in N2
                    if  H1.has_edge(v1, v2) or H2.has_edge(v1,v2)]
            log.debug("Tensor product edges for (%s,%s): %s" % (u1, u2, product_edges))
            edges += product_edges

    return edges


#TODO: What about edge ids?

