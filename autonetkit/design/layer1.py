import autonetkit.ank as ank_utils
import autonetkit.log as log


def build_layer1(anm):
    g_l1 = anm.add_overlay('layer1')
    g_phy = anm['phy']
    g_l1.add_nodes_from(g_phy)
    g_l1.add_edges_from(g_phy.edges())

    # aggregate collision domains
    hubs = g_l1.nodes(device_type="hub")
    ank_utils.aggregate_nodes(g_l1, hubs)
    # TODO: remove aggregated and disconnected nodes
    # refresh hubs list
    hubs = g_l1.nodes(device_type="hub")

    for hub in hubs:
        hub.collision_domain = True

    split_ptp(anm)
    build_layer1_conn(anm)

def build_layer1_conn(anm):
    g_l1 = anm['layer1']
    g_l1_conn = anm.add_overlay('layer1_conn')
    g_l1_conn.add_nodes_from(g_l1, retain="collision_domain")
    g_l1_conn.add_edges_from(g_l1.edges())

    collision_domains = g_l1_conn.nodes(collision_domain=True)
    exploded_edges = ank_utils.explode_nodes(g_l1_conn, collision_domains)

    # explode each seperately?
    for edge in exploded_edges:
        edge.multipoint = True
        edge.src_int.multipoint = True
        edge.dst_int.multipoint = True

    # TODO: tidy up partial repetition of collision_domain attribute and
    # device type


def split_ptp(anm):
    g_l1 = anm['layer1']
    g_phy = anm['phy']

    edges_to_split = [e for e in g_l1.edges()]
    edges_to_split = [e for e in edges_to_split
                      if not (e.src.is_hub() or e.dst.is_hub())]

    # TODO: debug the edges to split
    # print "edges to split", edges_to_split
    for edge in edges_to_split:
        edge.split = True  # mark as split for use in building nidb

    split_created_nodes = list(ank_utils.split(g_l1, edges_to_split,
                                               retain=['split'],
                                               id_prepend='cd_'))

    for node in split_created_nodes:
        node.device_type = "collision_domain"
        node.collision_domain = True

    # TODO: if parallel nodes, offset
    # TODO: remove graphics, assign directly
    g_graphics = anm['graphics']

    if len(g_graphics):
        co_ords_overlay = g_graphics  # source from graphics overlay
    else:
        co_ords_overlay = g_phy  # source from phy overlay

    for node in split_created_nodes:
        node['graphics'].x = ank_utils.neigh_average(g_l1, node, 'x',
                                                     co_ords_overlay) + 0.1

        # temporary fix for gh-90

        node['graphics'].y = ank_utils.neigh_average(g_l1, node, 'y',
                                                     co_ords_overlay) + 0.1

        # temporary fix for gh-90

        asn = ank_utils.neigh_most_frequent(
            g_l1, node, 'asn', g_phy)  # arbitrary choice
        node['graphics'].asn = asn
        node.asn = asn  # need to use asn in IP overlay for aggregating subnets


# TODO: build layer 1 connectivity graph
