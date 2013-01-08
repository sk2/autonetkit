import autonetkit
import autonetkit.anm
import autonetkit.config
import autonetkit.load.graphml as graphml
import autonetkit.ank as ank_utils
import autonetkit.ank as ank
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

    build_ip(anm)
    return anm



def build_ip(anm):
    import itertools
    import autonetkit.plugins.ip as ip
    G_ip = anm.add_overlay("ip")
    G_in = anm['input']
    G_graphics = anm['graphics']
    G_phy = anm['phy']

    G_ip.add_nodes_from(G_in)
    G_ip.add_edges_from(G_in.edges(type="physical"))

    ank.aggregate_nodes(G_ip, G_ip.nodes("is_switch"), retain = "edge_id")

    edges_to_split = [edge for edge in G_ip.edges() if edge.attr_both("is_l3device")]
    split_created_nodes = list(ank.split(G_ip, edges_to_split, retain='edge_id'))
    for node in split_created_nodes:
        node['graphics'].x = ank.neigh_average(G_ip, node, "x", G_graphics)
        node['graphics'].y = ank.neigh_average(G_ip, node, "y", G_graphics)

    G_ip.update(split_created_nodes, collision_domain=True)

    for node in G_ip.nodes("collision_domain"):
        graphics_node = G_graphics.node(node)
        node.host = G_phy.node(node.neighbors().next()).host # Set host to be same as one of the neighbors (arbitrary choice)
        asn = ank.neigh_most_frequent(G_ip, node, "asn", G_phy) # arbitrary choice
        node.asn = asn

        graphics_node.asn = asn
        graphics_node.x = ank.neigh_average(G_ip, node, "x", G_graphics)

        graphics_node.device_type = "collision_domain"
        cd_label = "cd_" + "_".join(sorted(ank.neigh_attr(G_ip, node, "label", G_phy)))
        node.label = cd_label 
        graphics_node.label = cd_label

    ip.allocate_ips(G_ip)
