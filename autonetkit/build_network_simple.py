import autonetkit
import autonetkit.anm
import autonetkit.ank as ank
import itertools
import autonetkit.ank_messaging as ank_messaging
import autonetkit.config
settings = autonetkit.config.settings
import autonetkit.log as log
import autonetkit.load.graphml as graphml
import autonetkit.exception
import networkx as nx
import os

__all__ = ['build']

messaging = ank_messaging.AnkMessaging()

#TODO: seperate out load and build - build should take a ready made nx graph and work from there.... load should do file handling error checking etc
# Also makes automated testing easier!

def build(input_graph_string, timestamp):
    #TODO: move this out of main console wrapper
    anm = autonetkit.anm.AbstractNetworkModel()
    
    input_graph = graphml.load_graphml(input_graph_string)

    G_in = anm.add_overlay("input", graph = input_graph)

#TODO: make these defaults
    G_in.update(G_in.nodes("is_router", platform = "junosphere"), syntax="junos")
    G_in.update(G_in.nodes("is_router", platform = "dynagen"), syntax="ios")
    G_in.update(G_in.nodes("is_router", platform = "netkit"), syntax="quagga")
    #G_in.update(G_in.nodes("is_router", platform = "cisco"), syntax="ios2")

    G_graphics = anm.add_overlay("graphics") # plotting data
    G_graphics.add_nodes_from(G_in, retain=['x', 'y', 'device_type', 'asn'])

    build_phy(anm)
    
    G_phy = anm['phy']

    routers = list(G_in.nodes("is_router"))
    G_ospf = anm.add_overlay("ospf", routers)
    G_ospf.add_edges_from(e for e in G_in.edges() if e.src.asn == e.dst.asn)

    G_ebgp = anm.add_overlay("ebgp", routers, directed = True)
    G_ebgp.add_edges_from((e for e in G_in.edges() if e.src.asn != e.dst.asn), bidirectional = True)

    G_ibgp = anm.add_overlay("ibgp", routers, directed = True)
    ibgp_edges = [ (s, t) for s in routers for t in routers if s.asn == t.asn]
    G_ibgp.add_edges_from(ibgp_edges, bidirectional = True)
    

    # thesis examples

    return anm


def boundary_nodes(G, nodes):
    #TODO: move to utils
    """ returns nodes at boundary of G
    TODO: check works for both directed and undirected graphs
    based on edge_boundary from networkx """
    import autonetkit.ank as ank_utils
    graph = ank_utils.unwrap_graph(G)
    nodes = list(nodes)
    nbunch = list(ank_utils.unwrap_nodes(nodes))
    # find boundary
    b_edges = nx.edge_boundary(graph, nbunch) # boundary edges
    internal_nodes = [s for (s, t) in b_edges]
    assert(all(n in nbunch for n in internal_nodes)) # check internal 

    return ank_utils.wrap_nodes(G, internal_nodes)
#TODO: catch AssertionError, handle through logging/warning
# Node boundary returns external nodes connected to nodes in nbunch
# for now use edge boundary, and find any node in nbunch connected to these edges


def build_bgp(anm):
    # eBGP
    G_phy = anm['phy']
    G_in = anm['input']
    G_bgp = anm.add_overlay("bgp", directed = True)
    G_bgp.add_nodes_from(G_in.nodes("is_router"))
    ebgp_edges = [edge for edge in G_in.edges() if not edge.attr_equal("asn")]
    G_bgp.add_edges_from(ebgp_edges, bidirectional = True, type = 'ebgp')


#TODO: here we want to map to lo0
    for node in G_bgp:
        for interface in node:
            interface.speed = 100

# now iBGP
#TODO: add flag for three iBGP types: full-mesh, algorithmic, custom
    if False:
        #TODO: need to allow manually set ibgp_level2 and ibgp_level1 groups, fallback is region/asn
        ank.copy_attr_from(G_in, G_phy, "region") 
        for asn, devices in G_phy.groupby("asn").items():
            as_graph = G_phy.subgraph(devices)
# want to group by asn, then group by region
            for region, region_devices in as_graph.groupby("region").items():
                b_nodes = boundary_nodes(as_graph, region_devices)
                route_reflectors = list(b_nodes) #TODO: may want to limit number if boundary nodes to set as route reflector
# eg could sort, choose most connected, most central, etc
                for n in route_reflectors:
                    log.debug("Setting rr for %s" % n)
                    G_bgp.node(n).route_reflector = True

                rr_clients = set(region_devices) - set(route_reflectors)

                # now connect region devices
                # rr to rr (over)
                over_links = [(rr1, rr2) for (rr1, rr2) in itertools.product(route_reflectors, route_reflectors)]
                G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')

                # rr to rrc (down)
                down_links = [(rr, client) for (rr, client) in itertools.product(route_reflectors, rr_clients)]
                G_bgp.add_edges_from(down_links, type = 'ibgp', direction = 'down')

                # rrc to rr (up)
                up_links = [(client, rr) for (client, rr) in itertools.product(rr_clients, route_reflectors)]
                G_bgp.add_edges_from(up_links, type = 'ibgp', direction = 'up')

            # and connect all Route-reflectors in the same AS
            asn_rrs = list(G_bgp.nodes(asn=asn, route_reflector = True))
            over_links = [(rr1, rr2) for (rr1, rr2) in itertools.product(asn_rrs, asn_rrs)]
            G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')

    if True:
        ank.copy_attr_from(G_in, G_bgp, "ibgp_level") 
        ank.copy_attr_from(G_in, G_bgp, "ibgp_l2_cluster") 
        ank.copy_attr_from(G_in, G_bgp, "ibgp_l3_cluster") 
        for node in G_bgp:
            #set defaults
#TODO: map "None" string to None for attributes from Graphml
            if not node.ibgp_level or node.ibgp_level == "None":
                node.ibgp_level = 1

            node.ibgp_level = int(node.ibgp_level) # ensure is numeric

            if not node.ibgp_l2_cluster or node.ibgp_l2_cluster == "None":
                node.ibgp_l2_cluster = node.region or "default_l2_cluster" # ibgp_l2_cluster defaults to region
                #TODO: check region exists
            if not node.ibgp_l3_cluster or node.ibgp_l3_cluster == "None":
                node.ibgp_l3_cluster = node.asn # ibgp_l3_cluster defaults to ASN

        for asn, devices in G_phy.groupby("asn").items():
            as_graph = G_phy.subgraph(devices)
            routers = list(n for n in as_graph if n.is_router)
#TODO: catch integer cast exception
            ibgp_levels = set(int(G_bgp.node(r).ibgp_level) for r in routers)
            max_level = max(ibgp_levels)
            all_pairs = [ (G_bgp.node(s), G_bgp.node(t)) for s in routers for t in routers if s != t]
            if max_level == 3:
                l1_l2_up_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == 1 and t.ibgp_level == 2
                        and s.ibgp_l2_cluster == t.ibgp_l2_cluster]
                l1_l2_down_links = [ (t, s) for (s, t) in l1_l2_up_links] # the reverse
                G_bgp.add_edges_from(l1_l2_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l1_l2_down_links, type = 'ibgp', direction = 'down')

                l2_peer_links = [ (s, t) for (s, t) in all_pairs 
                        if s.ibgp_level == t.ibgp_level == 2 and s.ibgp_l2_cluster == t.ibgp_l2_cluster ]
                G_bgp.add_edges_from(l2_peer_links, type = 'ibgp', direction = 'over')

                l2_l3_up_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == 2 and t.ibgp_level == 3
                        and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
                l2_l3_down_links = [ (t, s) for (s, t) in l2_l3_up_links] # the reverse
                G_bgp.add_edges_from(l2_l3_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l2_l3_down_links, type = 'ibgp', direction = 'down')

                l3_peer_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == t.ibgp_level == 3]
                G_bgp.add_edges_from(l3_peer_links, type = 'ibgp', direction = 'over')

            if max_level == 2:
                l1_l2_up_links = [ (s, t) for (s, t) in all_pairs 
                        if s.ibgp_level == 1 and t.ibgp_level == 2
                        and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
                l1_l2_down_links = [ (t, s) for (s, t) in l1_l2_up_links] # the reverse
                G_bgp.add_edges_from(l1_l2_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l1_l2_down_links, type = 'ibgp', direction = 'down')

                l2_peer_links = [ (s, t) for (s, t) in all_pairs 
                        if s.ibgp_level == t.ibgp_level == 2 and s.ibgp_l3_cluster == t.ibgp_l3_cluster ]
                G_bgp.add_edges_from(l2_peer_links, type = 'ibgp', direction = 'over')

            elif max_level == 1:
# full mesh
                l1_peer_links = [ (s, t) for (s, t) in all_pairs 
                if s.ibgp_l3_cluster == t.ibgp_l3_cluster ]
                G_bgp.add_edges_from(l1_peer_links, type = 'ibgp', direction = 'over')

    elif len(G_phy) < 5:
# full mesh
        for asn, devices in G_phy.groupby("asn").items():
            routers = [d for d in devices if d.is_router]
            ibgp_edges = [ (s, t) for s in routers for t in routers if s!=t]
            G_bgp.add_edges_from(ibgp_edges, type = 'ibgp')
    else:
        import autonetkit.plugins.route_reflectors as route_reflectors
        route_reflectors.allocate(G_phy, G_bgp)

#TODO: probably want to use l3 connectivity graph for allocating route reflectors

    ebgp_nodes = [d for d in G_bgp if any(edge.type == 'ebgp' for edge in d.edges())]
    G_bgp.update(ebgp_nodes, ebgp=True)

    for edge in G_bgp.edges(type = 'ibgp'):
        #TODO: need interface querying/selection. rather than hard-coded ids
        edge.bind_interface(edge.src, 0)

    for node in G_bgp:
        node._interfaces[0]['description'] = "loopback0"
def build_ip6(anm):
    import autonetkit.plugins.ip6 as ip6
    # uses the nodes and edges from ipv4
#TODO: make the nodes/edges common for IP, and then allocate after these
#TODO: globally replace ip with ip4
    G_ip6 = anm.add_overlay("ip6")
    G_in = anm['input']
    G_ip4 = anm['ip']
    G_ip6.add_nodes_from(G_ip4, retain="collision_domain") # retain if collision domain or not
    G_ip6.add_edges_from(G_ip4.edges())
    ip6.allocate_ips(G_ip6) 

def build_phy(anm):
    G_in = anm['input']
    G_phy = anm['phy']
    G_phy.add_nodes_from(G_in, retain=['label', 'update', 'device_type', 'device_subtype', 'asn', 'platform', 'host', 'syntax'])
    if G_in.data.Creator == "Topology Zoo Toolset":
        ank.copy_attr_from(G_in, G_phy, "Network") #TODO: move this into graphml (and later gml) reader

    G_phy.add_edges_from(G_in.edges(type="physical"))


