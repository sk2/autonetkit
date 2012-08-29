import autonetkit.ank as ank_utils
import autonetkit.log as log
import networkx as nx
import itertools

def allocate(G_phy, G_bgp):
    log.info("Allocating route reflectors")
    graph_phy = G_phy._graph
    for asn, devices in G_phy.groupby("asn").items():
        routers = [d for d in devices if d.is_router]
        router_ids = ank_utils.unwrap_nodes(routers)

        subgraph_phy = graph_phy.subgraph(router_ids)
        if len(subgraph_phy) == 1:  
                continue # single node in graph, no ibgp

        betw_cen = nx.degree_centrality(subgraph_phy)

        ordered = sorted(subgraph_phy.nodes(), key = lambda x: betw_cen[x], reverse = True)

        rr_count = len(subgraph_phy)/5 # Take top 20% to be route reflectors
        route_reflectors = ordered[:rr_count] # most connected 20%
        rr_clients = ordered[rr_count:] # the other routers
        route_reflectors = list(ank_utils.wrap_nodes(G_bgp, route_reflectors))
        rr_clients = list(ank_utils.wrap_nodes(G_bgp, rr_clients))

        G_bgp.update(route_reflectors, route_reflector = True) # mark as route reflector
        # rr <-> rr
        over_links = [(rr1, rr2) for rr1 in route_reflectors for rr2 in route_reflectors if rr1 != rr2] 
        G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')
        # client -> rr
        up_links = [(client, rr) for (client, rr) in itertools.product(rr_clients, route_reflectors)]
        G_bgp.add_edges_from(up_links, type = 'ibgp', direction = 'up')
        # rr -> client
        down_links = [(rr, client) for (client, rr) in up_links] # opposite of up
        G_bgp.add_edges_from(down_links, type = 'ibgp', direction = 'down')

    log.debug("iBGP done")
