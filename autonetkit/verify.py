import autonetkit.log as log
from autonetkit.ank_utils import unwrap_graph, unwrap_nodes
import pprint
from collections import defaultdict

def igp_routes(anm, measured):
    #TODO: split up expected calculation and comparison so don't need to calculate SPF multiple times
    #TODO: allow choice of IGP - for now is just OSPF
    import networkx as nx
    g_ipv4 = anm['ipv4']
    g_ospf = anm['ospf']

    log.info("Verifying IGP routes")

    # extract source node from measured data
    try:
        src_node = measured[0][0]
    except IndexError:
        log.info("Unable to parse measured results, returning")
        return


    # calculate expected routes


    prefixes_by_router = {}
    prefix_reachability = defaultdict(list)
    for router in g_ospf:
        ipv4_node = g_ipv4.node(router)
        neighbors = ipv4_node.neighbors()
        neighbor_subnets = [n.subnet for n in neighbors]
        prefixes_by_router[router] = neighbor_subnets
        for subnet in neighbor_subnets:
            # use strings for faster matching from here on 
            # (can convert back to overlay_nodes later)
            prefix_reachability[str(subnet)].append(str(router))

    #print prefixes_by_router
    #print prefix_reachability

    graph = unwrap_graph(g_ospf)

    shortest_paths = nx.shortest_path(graph, source = src_node, weight = 'cost')
    shortest_path_lengths = nx.shortest_path_length(graph, source = src_node, weight = 'cost')
    #pprint.pprint(shortest_path_lengths)

    optimal_prefixes = {}
    for prefix, routers in prefix_reachability.items():
        # decorate with cost
        try:
            routers_with_costs = [(shortest_path_lengths[r], r) for r in routers]
        except KeyError:
            continue # no router, likely from eBGP
        min_cost = min(rwc[0] for rwc in routers_with_costs)
        shortest_routers = [rwc[1] for rwc in routers_with_costs if rwc[0] == min_cost]
        optimal_prefixes[str(prefix)] = shortest_routers
    #print optimal_prefixes

    verified_prefixes = {}
    for route in measured:
        dst_cd = route[-1]
        prefix = str(g_ipv4.node(dst_cd).subnet)
        try:
            optimal_routers = optimal_prefixes[prefix]
        except KeyError:
            continue # prefix not present
        if src_node in optimal_routers:
            continue # target is self

        optimal_routes = [shortest_paths[r] for r in optimal_routers]
        optimal_next_hop = [p[1] for p in optimal_routes]
        actual_next_hop = route[1]

        log.info( "Match: %s, %s, optimal: %s, actual: %s" % (
                actual_next_hop in optimal_next_hop, prefix, ", ".join(optimal_next_hop), actual_next_hop))

        if actual_next_hop not in optimal_next_hop:
            log.info("Unverified prefix: %s on %s. Expected: %s. Received: %s" % (prefix, dst_cd,
                ", ".join(optimal_next_hop), actual_next_hop))

        verified_prefixes[prefix] = actual_next_hop in optimal_next_hop


    verified_count = verified_prefixes.values().count(True) 
    try:
        verified_fraction = round(100 * verified_count/len(verified_prefixes),2)
    except ZeroDivisionError:
        verified_fraction = 0
    log.info("%s%% verification rate" % verified_fraction)
        
    return verified_prefixes
