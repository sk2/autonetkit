"""Module to build overlay graphs for network design"""

import autonetkit
import autonetkit.ank as ank_utils
import autonetkit.anm
import autonetkit.config
import autonetkit.exception
import autonetkit.log as log
import networkx as nx

SETTINGS = autonetkit.config.settings

# TODO: revisit phy_neighbors for eg ASN and use layer3 instead

__all__ = ['build']


def load(input_graph_string, defaults = True):

    # TODO: look at XML header for file type
    import autonetkit.load.graphml as graphml
    import autonetkit.load.load_json as load_json
    try:
        input_graph = graphml.load_graphml(input_graph_string, defaults=defaults)
    except autonetkit.exception.AnkIncorrectFileFormat:
        try:
            input_graph = load_json.load_json(input_graph_string, defaults=defaults)
        except (ValueError, autonetkit.exception.AnkIncorrectFileFormat):
            # try a different reader
            try:
                from autonetkit_cisco import load as cisco_load
            except ImportError, error:
                log.debug("Unable to load autonetkit_cisco %s", error)
                return  # module not present (development module)
            else:
                input_graph = cisco_load.load(input_graph_string)
                # add local deployment host
                SETTINGS['General']['deploy'] = True
                SETTINGS['Deploy Hosts']['internal'] = {
                    'VIRL': {
                        'deploy': True,
                    },
                }

    return input_graph


def grid_2d(dim):
    """Creates a 2d grid of dimension dim"""
    graph = nx.grid_2d_graph(dim, dim)

    for node in graph:
        graph.node[node]['asn'] = 1
        graph.node[node]['x'] = node[0] * 150
        graph.node[node]['y'] = node[1] * 150
        graph.node[node]['device_type'] = 'router'
        graph.node[node]['platform'] = 'cisco'
        graph.node[node]['syntax'] = 'ios_xr'
        graph.node[node]['host'] = 'internal'
        graph.node[node]['ibgp_role'] = "Peer"

    mapping = {node: "%s_%s" % (node[0], node[1]) for node in graph}
    # Networkx wipes data if remap with same labels
    nx.relabel_nodes(graph, mapping, copy=False)
    for src, dst in graph.edges():
        graph[src][dst]['type'] = "physical"
        # add global index for sorting

    SETTINGS['General']['deploy'] = True
    SETTINGS['Deploy Hosts']['internal'] = {
        'cisco': {
            'deploy': True,
        },
    }

    return graph


def initialise(input_graph):
    """Initialises the input graph with from a NetworkX graph"""
    all_multigraph = input_graph.is_multigraph()
    anm = autonetkit.anm.NetworkModel(all_multigraph=all_multigraph)

    g_in = anm.initialise_input(input_graph)
    # autonetkit.update_vis(anm)

# set defaults
    if not g_in.data.specified_int_names:
        # if not specified then automatically assign interface names
        g_in.data.specified_int_names = False

    #import autonetkit.plugins.graph_product as graph_product
    # graph_product.expand(g_in)  # apply graph products if relevant

    expand_fqdn = False
    # TODO: make this set from config and also in the input file
    if expand_fqdn and len(ank_utils.unique_attr(g_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn
        anm.set_node_label(".", ['label', 'asn'])

    g_in.update(g_in.routers(platform="junosphere"), syntax="junos")
    g_in.update(g_in.routers(platform="dynagen"), syntax="ios")
    g_in.update(g_in.routers(platform="netkit"), syntax="quagga")
    # TODO: is this used?
    g_in.update(g_in.servers(platform="netkit"), syntax="quagga")

    #TODO: check this is needed
    #autonetkit.ank.set_node_default(g_in, specified_int_names=None)

    g_graphics = anm.add_overlay("graphics")  # plotting data
    g_graphics.add_nodes_from(g_in, retain=['x', 'y', 'device_type',
                                            'label', 'device_subtype', 'asn'])

    return anm


def check_server_asns(anm):
    """Checks that servers have appropriate ASN allocated.
    Warns and auto-corrects servers connected to routers of a different AS
    #TODO: provide manual over-ride for this auto-correct.
    """
    # TODO: Move to validate module?
    g_phy = anm['phy']

    for server in g_phy.servers():
        if server.device_subtype in ("SNAT", "FLAT"):
            continue  # Don't warn on ASN for NAT elements
        l3_neighbors = list(server['layer3'].neighbors())
        l3_neighbor_asns = set(n.asn for n in l3_neighbors)
        if server.asn not in l3_neighbor_asns:
            neighs_with_asn = ["%s: AS %s" % (n, n.asn)
                               for n in l3_neighbors]
            # tuples for warning message
            server.log.warning("Server does not belong to same ASN "
                               "as neighbors %s" % (neighs_with_asn))

            if len(l3_neighbors) == 1:
                # single ASN of neighbor -> auto correct
                if server['input'].default_asn:
                    neigh_asn = l3_neighbor_asns.pop()
                    log.warning("Updating server %s AS from %s"
                                " to %s", server, server.asn, neigh_asn)
                    server.asn = neigh_asn
                else:
                    log.info("Server %s ASN %s explictly set by user, "
                             "not auto-correcting", server, server.asn)


def apply_design_rules(anm):
    """Applies appropriate design rules to ANM"""
    # log.info("Building overlay topologies")
    g_in = anm['input']

    build_phy(anm)

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, e:
        log.debug("Unable to load autonetkit_cisco %s", e)
    else:
        cisco_build_network.post_phy(anm)

    g_phy = anm['phy']
    from autonetkit.design.osi_layers import build_layer2, build_layer3
    # log.info("Building layer2")
    build_layer2(anm)

    # log.info("Building layer3")
    build_layer3(anm)

    check_server_asns(anm)

    from autonetkit.design.mpls import build_vrf
    build_vrf(anm)  # do before to add loopbacks before ip allocations
    from autonetkit.design.ip import build_ip, build_ipv4, build_ipv6
    # TODO: replace this with layer2 overlay topology creation
    # log.info("Allocating IP addresses")
    build_ip(anm)  # ip infrastructure topology

    address_family = g_in.data.address_family or "v4"  # default is v4
# TODO: can remove the infrastructure now create g_ip seperately
    if address_family == "None":
        log.info("IP addressing disabled, disabling routing protocol ",
                 "configuration")
        anm['phy'].data.enable_routing = False

    if address_family == "None":
        log.info("IP addressing disabled, skipping IPv4")
        anm.add_overlay("ipv4")  # create empty so rest of code follows
        g_phy.update(g_phy, use_ipv4=False)
    elif address_family in ("v4", "dual_stack"):
        build_ipv4(anm, infrastructure=True)
        g_phy.update(g_phy, use_ipv4=True)
    elif address_family == "v6":
        # Allocate v4 loopbacks for router ids
        build_ipv4(anm, infrastructure=False)
        g_phy.update(g_phy, use_ipv4=False)

    # TODO: Create collision domain overlay for ip addressing - l2 overlay?
    if address_family == "None":
        log.info("IP addressing disabled, not allocating IPv6")
        anm.add_overlay("ipv6")  # create empty so rest of code follows
        g_phy.update(g_phy, use_ipv6=False)
    elif address_family in ("v6", "dual_stack"):
        build_ipv6(anm)
        g_phy.update(g_phy, use_ipv6=True)
    else:
        anm.add_overlay("ipv6")  # placeholder for compiler logic

    default_igp = g_in.data.igp or "ospf"
    ank_utils.set_node_default(g_in, igp=default_igp)
    ank_utils.copy_attr_from(g_in, g_phy, "igp")

    ank_utils.copy_attr_from(g_in, g_phy, "include_csr")

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, error:
        log.debug("Unable to load autonetkit_cisco %s" % error)
    else:
        cisco_build_network.pre_design(anm)

    # log.info("Building IGP")
    from autonetkit.design.igp import build_igp
    build_igp(anm)

    # log.info("Building BGP")
    from autonetkit.design.bgp import build_bgp
    build_bgp(anm)
    # autonetkit.update_vis(anm)

    from autonetkit.design.mpls import mpls_te, mpls_oam
    mpls_te(anm)
    mpls_oam(anm)

# post-processing
    if anm['phy'].data.enable_routing:
        from autonetkit.design.mpls import (mark_ebgp_vrf,
                                            build_ibgp_vpn_v4)
        mark_ebgp_vrf(anm)
        build_ibgp_vpn_v4(anm)  # build after bgp as is based on
    # autonetkit.update_vis(anm)

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, error:
        log.debug("Unable to load autonetkit_cisco %s", error)
    else:
        cisco_build_network.post_design(anm)

    # log.info("Finished building network")
    return anm


def build(input_graph):
    """Main function to build network overlay topologies"""
    anm = None
    anm = initialise(input_graph)
    anm = apply_design_rules(anm)
    return anm

def build_phy(anm):
    """Build physical overlay"""
    g_in = anm['input']
    g_phy = anm['phy']

    g_phy.data.enable_routing = g_in.data.enable_routing
    if g_phy.data.enable_routing is None:
        g_in.data.enable_routing = True  # default if not set

    g_phy.add_nodes_from(g_in, retain=['label', 'update', 'device_type',
                                       'asn', 'specified_int_names', 'x', 'y',
                                       'device_subtype', 'platform', 'host', 'syntax'])

    if g_in.data.Creator == "Topology Zoo Toolset":
        ank_utils.copy_attr_from(g_in, g_phy, "Network")

    ank_utils.set_node_default(g_phy, Network=None)
    g_phy.add_edges_from(g_in.edges(type="physical"))
    # TODO: make this automatic if adding to the physical graph?

    ank_utils.set_node_default(g_phy, use_ipv4=False, use_ipv6=False)
    ank_utils.copy_attr_from(g_in, g_phy, "custom_config_global",
                             dst_attr="custom_config")

    for node in g_phy:
        if node['input'].custom_config_loopback_zero:
            lo_zero_config = node['input'].custom_config_loopback_zero
            node.loopback_zero.custom_config = lo_zero_config
        custom_config_phy_ints = node['input'].custom_config_phy_ints
        for interface in node:
            if custom_config_phy_ints:
                interface.custom_config = custom_config_phy_ints
            specified_id = interface['input'].get("specified_id")
            if specified_id:
                interface.specified_id = specified_id  # map across

    for node in g_phy:
        for interface in node:
            remote_edges = interface.edges()
            if len(remote_edges):
                interface.description = 'to %s' \
                % remote_edges[0].dst.label


def build_conn(anm):
    """Build connectivity overlay"""
    g_in = anm['input']
    g_conn = anm.add_overlay("conn", directed=True)
    g_conn.add_nodes_from(g_in, retain=['label'])
    g_conn.add_edges_from(g_in.edges(type="physical"))

    return
