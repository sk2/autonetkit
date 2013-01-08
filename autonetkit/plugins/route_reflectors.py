import autonetkit.ank as ank_utils
import autonetkit.log as log
import networkx as nx
import pprint
import itertools
import autonetkit.log as log

#TODO: need to handle case of switches along path.... won't work for just router connectivity path lengths
def allocate(G_phy, G_bgp):
    log.info("Allocating route reflectors")
    graph_phy = G_phy._graph
    for asn, devices in G_phy.groupby("asn").items():
        routers = [d for d in devices if d.is_router]
        router_ids = list(ank_utils.unwrap_nodes(routers))
        mapping_id_to_device = dict(zip(router_ids, routers)) # to reverse lookup id back to device

        subgraph_phy = graph_phy.subgraph(router_ids)
        if len(subgraph_phy) == 1:  
                continue # single node in graph, no ibgp

        betw_cen = nx.degree_centrality(subgraph_phy)

        ordered = sorted(subgraph_phy.nodes(), key = lambda x: betw_cen[x], reverse = True)

        rr_count = len(subgraph_phy)/4 or 1# Take top 20% to be route reflectors
        route_reflectors = ordered[:rr_count] # most connected x%
        log.debug("Chose route_reflectors %s" % route_reflectors)
        rr_clients = ordered[rr_count:] # the other routers
        route_reflectors = list(ank_utils.wrap_nodes(G_bgp, route_reflectors))
        rr_clients = list(ank_utils.wrap_nodes(G_bgp, rr_clients))

# distances (shortest path, physical graph) from rrs to clients
        path_lengths = {}
        for rr in route_reflectors:
            path = nx.single_source_shortest_path_length(subgraph_phy, rr)
            path_mapped = dict( (mapping_id_to_device[id], length) for (id, length) in path.items()) # ids to devices
            path_lengths[rr] = path_mapped

        G_bgp.update(route_reflectors, route_reflector = True) # mark as route reflector
        # rr <-> rr
        over_links = [(rr1, rr2) for rr1 in route_reflectors for rr2 in route_reflectors if rr1 != rr2] 
        G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')

        for client in rr_clients:
            ranked_rrs = sorted(route_reflectors, key = lambda rr: path_lengths[rr][client])
            parent_count = 2 # number of parents to connect to for each rr client
            parent_rrs = ranked_rrs[:parent_count]
            log.info("Route reflectors for %s are %s " % (client, parent_rrs))

            for parent in parent_rrs:
                # client -> rr
                #up_links = [(client, rr) for (client, rr) in itertools.product(rr_clients, route_reflectors)]
                G_bgp.add_edge(client, parent, type = 'ibgp', direction = 'up')
                # rr -> client
                #down_links = [(rr, client) for (client, rr) in up_links] # opposite of up
                G_bgp.add_edge(parent, client, type = 'ibgp', direction = 'down')

    log.debug("iBGP done")
