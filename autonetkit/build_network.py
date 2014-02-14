"""Module to build overlay graphs for network design"""
import itertools

import autonetkit
import autonetkit.ank as ank_utils
import autonetkit.ank_messaging as ank_messaging
import autonetkit.anm
import autonetkit.config
import autonetkit.exception
import autonetkit.load.graphml as graphml
import autonetkit.log as log
import networkx as nx
from autonetkit.exception import AutoNetkitException

SETTINGS = autonetkit.config.settings

#TODO: revisit phy_neighbors for eg ASN and use l3_conn instead

#TODO: note that build network now assumes input graph has interface mappings on nodes/edges

__all__ = ['build']
from autonetkit.ank_utils import call_log

@call_log
def load(input_graph_string):
    #TODO: look at XML header for file type
    try:
        input_graph = graphml.load_graphml(input_graph_string)
    except autonetkit.exception.AnkIncorrectFileFormat:
# try a different reader
        try:
            from autonetkit_cisco import load as cisco_load
        except ImportError, e:
            log.debug("Unable to load autonetkit_cisco %s" % e)
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

@call_log
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
    for index, (src, dst) in enumerate(graph.edges()):
        graph[src][dst]['type'] = "physical"
        # add global index for sorting

    SETTINGS['General']['deploy'] = True
    SETTINGS['Deploy Hosts']['internal'] = {
        'cisco': {
        'deploy': True,
        },
    }

    return graph

@call_log
def initialise(input_graph):
    """Initialises the input graph with from a NetworkX graph"""
    anm = autonetkit.anm.AbstractNetworkModel()

    input_undirected = nx.Graph(input_graph)
    g_in = anm.add_overlay("input", graph=input_undirected)

# set defaults
    if not g_in.data.specified_int_names:
        # if not specified then automatically assign interface names
        g_in.data.specified_int_names = False

    #import autonetkit.plugins.graph_product as graph_product
    #graph_product.expand(g_in)  # apply graph products if relevant

    expand_fqdn = False
    # TODO: make this set from config and also in the input file
    if expand_fqdn and len(ank_utils.unique_attr(g_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn
        anm.set_node_label(".", ['label', 'asn'])

    g_in.update(g_in.routers(platform="junosphere"), syntax="junos")
    g_in.update(g_in.routers(platform="dynagen"), syntax="ios")
    g_in.update(g_in.routers(platform="netkit"), syntax="quagga")
    #TODO: is this used?
    g_in.update(g_in.servers(platform="netkit"), syntax="quagga")

    autonetkit.ank.set_node_default(g_in,  specified_int_names=None)

    g_graphics = anm.add_overlay("graphics")  # plotting data
    g_graphics.add_nodes_from(g_in, retain=['x', 'y', 'device_type',
        'label', 'device_subtype', 'asn'])

    if g_in.data.Creator == "VIRL":
        #TODO: move this to other module
        # Multiple ASNs set, use label format device.asn
        #anm.set_node_label(".", ['label_full'])
        pass

    return anm

@call_log
def check_server_asns(anm):
    """Checks that servers have appropriate ASN allocated.
    Warns and auto-corrects servers which are connected to routers of a difference AS.
    #TODO: provide manual over-ride for this auto-correct.
    """
    #TODO: Move to validate module?
    g_phy = anm['phy']

    for server in g_phy.servers():
        if server.device_subtype in ("SNAT", "FLAT"):
            continue # Don't warn on ASN for NAT elements
        l3_neighbors = list(server['l3_conn'].neighbors())
        l3_neighbor_asns = set(n.asn for n in l3_neighbors)
        if server.asn not in l3_neighbor_asns:
            neighs_with_asn = ["%s: AS %s" % (n, n.asn)
                for n in l3_neighbors] # tuples for warning message
            server.log.warning("Server does not belong to same ASN as neighbors %s" % (neighs_with_asn))

            if len(l3_neighbors) == 1:
                # single ASN of neighbor -> auto correct
                if server['input'].default_asn:
                    neigh_asn = l3_neighbor_asns.pop()
                    log.warning("Updating server %s AS from %s to %s" % (server, server.asn, neigh_asn))
                    server.asn = neigh_asn
                else:
                    log.info("Server %s ASN %s explictly set by user, not auto-correcting" %
                        (server, server.asn))


@call_log
def apply_design_rules(anm):
    """Applies appropriate design rules to ANM"""
    g_in = anm['input']

    build_phy(anm)
    g_phy = anm['phy']

    build_l3_connectivity(anm)
    check_server_asns(anm)

    from autonetkit.design.mpls import build_vrf
    build_vrf(anm) # need to do before to add loopbacks before ip allocations
    from autonetkit.design.ip import build_ip, build_ipv4, build_ipv6
    #TODO: replace this with layer2 overlay topology creation
    build_ip(anm) # ip infrastructure topology

#TODO: set defaults at the start, rather than inline, ie set g_in.data.address_family then use later

    address_family = g_in.data.address_family or "v4" # default is v4
#TODO: can remove the infrastructure now create g_ip seperately
    if address_family == "None":
        log.info("IP addressing disabled, disabling routing protocol configuration")
        anm['phy'].data.enable_routing = False

    if address_family == "None":
        log.info("IP addressing disabled, skipping IPv4")
        anm.add_overlay("ipv4") # create empty so rest of code follows through
        g_phy.update(g_phy, use_ipv4 = False)
    elif address_family in ("v4", "dual_stack"):
        build_ipv4(anm, infrastructure = True)
        g_phy.update(g_phy, use_ipv4 = True)
    elif address_family == "v6":
        # Allocate v4 loopbacks for router ids
        build_ipv4(anm, infrastructure = False)
        g_phy.update(g_phy, use_ipv4 = False)

    #TODO: Create a collision domain overlay for ip addressing - l2 overlay?
    if address_family == "None":
        log.info("IP addressing disabled, not allocating IPv6")
        anm.add_overlay("ipv6") # create empty so rest of code follows through
        g_phy.update(g_phy, use_ipv6 = False)
    elif address_family in ("v6", "dual_stack"):
        build_ipv6(anm)
        g_phy.update(g_phy, use_ipv6 = True)
    else:
        anm.add_overlay("ipv6") # placeholder for compiler logic

    default_igp = g_in.data.igp or "ospf"
    ank_utils.set_node_default(g_in,  igp=default_igp)

    ank_utils.copy_attr_from(g_in, g_phy, "include_csr")

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, e:
        log.debug("Unable to load autonetkit_cisco %s" % e)
    else:
        cisco_build_network.pre_design(anm)

    from autonetkit.design.igp import build_ospf, build_eigrp, build_isis
    build_ospf(anm)
    build_eigrp(anm)
    build_isis(anm)

    from autonetkit.design.bgp import build_bgp
    build_bgp(anm)
    #autonetkit.update_http(anm)

    from autonetkit.design.mpls import mpls_te, mpls_oam
    mpls_te(anm)
    mpls_oam(anm)

# post-processing
    if anm['phy'].data.enable_routing:
        from autonetkit.design.mpls import mark_ebgp_vrf, build_ibgp_vpn_v4
        mark_ebgp_vrf(anm)
        build_ibgp_vpn_v4(anm) # build after bgp as is based on
    #autonetkit.update_http(anm)

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, e:
        log.debug("Unable to load autonetkit_cisco %s" % e)
    else:
        cisco_build_network.post_design(anm)

    return anm


@call_log
def build(input_graph):
    """Main function to build network overlay topologies"""
    anm = None
    try:
        anm = initialise(input_graph)
        anm = apply_design_rules(anm)
        #print {str(node): {'x': node.x, 'y': node.y} for node in anm['input']}
        import autonetkit
        autonetkit.update_http(anm)
    except Exception, e:
        # Send the visualisation to help debugging
        import autonetkit
        try:
            autonetkit.update_http(anm)
        except Exception, e:
            # problem with vis -> could be coupled with original exception - raise original
            log.warning("Unable to visualise: %s" % e)
        raise # raise the original exception
    return anm


def remove_parallel_switch_links(anm):
    g_phy = anm['phy']
    subs = ank_utils.connected_subgraphs(g_phy, g_phy.switches())
    for component in subs:
        log.debug("Checking for multiple links to switch cluster %s" % str(sorted(component)))

        # Collect all links into this cluster
        external_edges = []
        for switch in component:
            for edge in switch.edges():
                if edge.dst not in component:
                    external_edges.append(edge)

        # Group by the node they link to
        from collections import defaultdict
        check_dict = defaultdict(list)
        for edge in external_edges:
            check_dict[edge.dst].append(edge)

        # Check to see if any nodes have more than one link into this aggregate
        for dst, edges in check_dict.items():
            if len(edges) > 1:
                edges_to_remove = sorted(edges)[1:] # remove all but first
                interfaces = ", ".join(sorted(str(edge.dst_int['phy']) for edge in edges))
                interfaces_to_disconnect = ", ".join(sorted(str(edge.dst_int['phy']) for edge in edges_to_remove))
                dst.log.warning("Multiple edges exist to same switch cluster: %s (%s). Removing edges from interfaces %s" % (
                    str(sorted(component)), interfaces, interfaces_to_disconnect))

                g_phy.remove_edges_from(edges_to_remove)

@call_log
def build_phy(anm):
    """Build physical overlay"""
    g_in = anm['input']
    g_phy = anm['phy']

    g_phy.data.enable_routing = g_in.data.enable_routing
    if g_phy.data.enable_routing is None:
        g_in.data.enable_routing = True # default if not set

    g_phy.add_nodes_from(g_in, retain=['label', 'update', 'device_type', 'asn',
        'specified_int_names',
        'device_subtype', 'platform', 'host', 'syntax'])
    if g_in.data.Creator == "Topology Zoo Toolset":
        ank_utils.copy_attr_from(g_in, g_phy, "Network")

    ank_utils.set_node_default(g_phy,  Network=None)
    g_phy.add_edges_from(g_in.edges(type="physical"))
    # TODO: make this automatic if adding to the physical graph?

    if g_in.data.Creator == "VIRL":
        g_phy.data.mgmt_interfaces_enabled = g_in.data.mgmt_interfaces_enabled
        #TODO: remove this code now allocated externally
        g_phy.data.mgmt_address_start = g_in.data.mgmt_address_start
        g_phy.data.mgmt_address_end = g_in.data.mgmt_address_end
        g_phy.data.mgmt_prefixlen = g_in.data.mgmt_prefixlen
        g_phy.data.mgmt_prefixlen = g_in.data.mgmt_prefixlen

        ank_utils.copy_attr_from(g_in, g_phy, "use_cdp")
        ank_utils.copy_attr_from(g_in, g_phy, "use_onepk")
        ank_utils.copy_attr_from(g_in, g_phy, "label_full")
        ank_utils.copy_attr_from(g_in, g_phy, "indices")
        ank_utils.copy_attr_from(g_in, g_phy, "dont_configure_static_routing")
        ank_utils.copy_attr_from(g_in, g_phy, "server_username")
        ank_utils.copy_attr_from(g_in, g_phy, "server_ssh_key")

    ank_utils.set_node_default(g_phy,  use_ipv4 = False, use_ipv6=False)

    g_phy.allocate_interfaces()

    for node in g_phy:
        for interface in node:
            specified_id = interface['input'].get("specified_id")
            if specified_id:
                interface.specified_id = specified_id # map across

    remove_parallel_switch_links(anm)

@call_log
def build_l3_connectivity(anm):
    """ creates l3_connectivity graph, which is switch nodes aggregated and exploded"""
    #TODO: use this as base for ospf, ebgp, ip, etc rather than exploding in each
    g_in = anm['input']
    g_l3conn = anm.add_overlay("l3_conn")
    g_l3conn.add_nodes_from(g_in, retain=['label', 'update', 'device_type', 'asn',
        'specified_int_names',
        'device_subtype', 'platform', 'host', 'syntax'])
    g_l3conn.add_nodes_from(g_in.switches(), retain=['asn'])
    g_l3conn.add_edges_from(g_in.edges())

    ank_utils.aggregate_nodes(g_l3conn, g_l3conn.switches())
    exploded_edges = ank_utils.explode_nodes(g_l3conn,
        g_l3conn.switches())
    for edge in exploded_edges:
        edge.multipoint = True
        edge.src_int.multipoint = True
        edge.dst_int.multipoint = True

@call_log
def build_conn(anm):
    """Build connectivity overlay"""
    g_in = anm['input']
    g_conn = anm.add_overlay("conn", directed=True)
    g_conn.add_nodes_from(g_in, retain=['label'])
    g_conn.add_edges_from(g_in.edges(type="physical"))

    return
