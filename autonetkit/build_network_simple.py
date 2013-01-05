import autonetkit
import autonetkit.anm
import autonetkit.config
import autonetkit.load.graphml as graphml
import autonetkit.ank as ank_utils
import networkx as nx

def build(input_data, timestamp):
    anm = autonetkit.anm.AbstractNetworkModel()
    input_graph = graphml.load_graphml(input_data)
    G_in = anm.add_overlay("input", graph = input_graph)

    G_graphics = anm.add_overlay("graphics") # plotting data
    G_graphics.add_nodes_from(G_in, retain=['x', 'y', 'device_type', 'asn'])
    
    G_phy = anm['phy']
    G_phy.add_nodes_from(G_in, retain=['label', 'device_type', 'asn', 'platform', 'host', 'syntax'])
    G_phy.add_edges_from(G_in.edges(type="physical"))

    routers = list(G_in.nodes("is_router"))
    G_ospf = anm.add_overlay("ospf", G_in.nodes("is_router"))
    G_ospf.add_edges_from(e for e in G_in.edges() if e.src.asn == e.dst.asn)

    G_ebgp = anm.add_overlay("ebgp", G_in.nodes("is_router"), directed = True)
    G_ebgp.add_edges_from((e for e in G_in.edges() if e.src.asn != e.dst.asn), bidirectional = True)

    G_ibgp = anm.add_overlay("ibgp", G_in.nodes("is_router"), directed = True)
    G_ibgp.add_edges_from(((s, t) for s in routers for t in routers if s.asn == t.asn), bidirectional = True)




    # hierarchical
    G_ibgp = anm.add_overlay("ibgp_rr", G_in.nodes("is_router"), directed = True)

    graph_phy = ank_utils.unwrap_graph(G_phy)
    centrality = nx.degree_centrality(graph_phy) 
    rrs = [n for n in centrality if centrality[n] > 0.13]

    for rr in rrs:
        G_ibgp.node(rr).route_reflector = True


    rrs = set(r for r in G_ibgp if r.route_reflector)
    clients = set(G_ibgp) - rrs
    G_ibgp.add_edges_from(((s, t) for s in clients for t in rrs), direction = "up")
    G_ibgp.add_edges_from(((s, t) for s in rrs for t in clients), direction = "down")
    G_ibgp.add_edges_from(((s, t) for s in rrs for t in rrs), direction = "over")




    
    return anm
