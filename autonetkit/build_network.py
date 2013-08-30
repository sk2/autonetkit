"""Module to build overlay graphs for network design"""
import autonetkit
import autonetkit.anm
import autonetkit.ank_messaging as ank_messaging
import autonetkit.config
SETTINGS = autonetkit.config.settings
import autonetkit.log as log
import autonetkit.load.graphml as graphml
import autonetkit.exception
import networkx as nx
import autonetkit.ank as ank_utils
import itertools

#TODO: remove retain edge_id once removed from compiler
#TODO: note that build network now assumes input graph has interface mappings on nodes/edges

__all__ = ['build']

MESSAGING = ank_messaging.AnkMessaging()

def load(input_graph_string):
    try:
        input_graph = graphml.load_graphml(input_graph_string)
    except autonetkit.exception.AnkIncorrectFileFormat:
# try a different reader
        try:
            from autonetkit_cisco import load as cisco_load
        except ImportError, e:
            log.debug("Unable to load autonetkit_cisco %s" % e)
            return  # module not present (development module)
        input_graph = cisco_load.load(input_graph_string)
# add local deployment host
        SETTINGS['General']['deploy'] = True
        SETTINGS['Deploy Hosts']['internal'] = {
            'cisco': {
            'deploy': True,
            },
        }

    return input_graph

def grid_2d(dim):
    """Creates a 2d grid of dimension dim"""
    import networkx as nx
    graph = nx.grid_2d_graph(dim, dim)

    for node in graph:
        graph.node[node]['asn'] = 1
        graph.node[node]['x'] = node[0] * 150
        graph.node[node]['y'] = node[1] * 150
        graph.node[node]['device_type'] = 'router'
        graph.node[node]['platform'] = 'cisco'
        graph.node[node]['syntax'] = 'ios_xr'
        graph.node[node]['host'] = 'internal'
        graph.node[node]['ibgp_level'] = 0

    mapping = {node: "%s_%s" % (node[0], node[1]) for node in graph}
    nx.relabel_nodes(graph, mapping, copy=False) # Networkx wipes data if remap with same labels
    for index, (src, dst) in enumerate(graph.edges()):
        graph[src][dst]['type'] = "physical"
        graph[src][dst]['edge_id'] = "%s_%s_%s" % (index, src, dst) # add global index for sorting

    SETTINGS['General']['deploy'] = True
    SETTINGS['Deploy Hosts']['internal'] = {
        'cisco': {
        'deploy': True,
        },
    }

    return graph

def initialise(input_graph):
    """Initialises the input graph with from a NetworkX graph"""
    anm = autonetkit.anm.AbstractNetworkModel()

    input_undirected = nx.Graph(input_graph)
    g_in = anm.add_overlay("input", graph=input_undirected)
    anm.add_overlay("input_directed", graph=input_graph, directed=True)

# set defaults
    if not g_in.data.specified_int_names:
        # if not specified then automatically assign interface names
        g_in.data.specified_int_names = False

    import autonetkit.plugins.graph_product as graph_product
    graph_product.expand(g_in)  # apply graph products if relevant

    expand_fqdn = False
    # TODO: make this set from config and also in the input file
    if expand_fqdn and len(ank_utils.unique_attr(g_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn
        anm.set_node_label(".", ['label', 'pop', 'asn'])

    g_in.update(
        g_in.nodes("is_router", platform="junosphere"), syntax="junos")
    g_in.update(g_in.nodes("is_router", platform="dynagen"), syntax="ios")
    g_in.update(g_in.nodes("is_router", platform="netkit"), syntax="quagga")
    g_in.update(g_in.nodes("is_server", platform="netkit"), syntax="quagga")

    g_graphics = anm.add_overlay("graphics")  # plotting data
    g_graphics.add_nodes_from(g_in, retain=['x', 'y', 'device_type',
        'label', 'device_subtype', 'pop', 'asn'])

    if g_in.data.Creator == "Maestro":
        # Multiple ASNs set, use label format device.asn
        anm.set_node_label(".", ['label_full'])

    autonetkit.update_http(anm)
    return anm

def apply_design_rules(anm):
    """Applies appropriate design rules to ANM"""
    g_in = anm['input']

    build_phy(anm)
    g_phy = anm['phy']

    import autonetkit
    autonetkit.update_http(anm)
    build_l3_connectivity(anm)

    build_vrf(anm) # need to do before to add loopbacks before ip allocations
    from autonetkit.design.ip import build_ip, build_ipv4,build_ipv6
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
    non_igp_nodes = [n for n in g_in if not n.igp]
#TODO: should this be modifying g_in?
    g_in.update(non_igp_nodes, igp=default_igp) # store igp onto each node

    ank_utils.copy_attr_from(g_in, g_phy, "include_csr")

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError, e:
        log.debug("Unable to load autonetkit_cisco %s" % e)
    else:
        cisco_build_network.pre_design(anm)

    import autonetkit.design.igp
    autonetkit.design.igp.build_ospf(anm)
    autonetkit.design.igp.build_eigrp(anm)
    autonetkit.design.igp.build_isis(anm)

    import autonetkit.design.bgp
    autonetkit.design.bgp.build_bgp(anm)
    autonetkit.update_http(anm)

# post-processing
    if anm['phy'].data.enable_routing:
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


def build(input_graph):
    """Main function to build network overlay topologies"""
    anm = initialise(input_graph)
    anm = apply_design_rules(anm)
    return anm

def vrf_pre_process(anm):
    """Marks nodes in g_in as appropriate based on vrf roles.
    CE nodes -> ibgp_level = 0, so not in ibgp (this is allocated later)
    """
    log.debug("Applying VRF pre-processing")
    g_vrf = anm['vrf']
    for node in g_vrf.nodes(vrf_role = "CE"):
        log.debug("Marking CE node %s as non-ibgp" % node)
        node['input'].ibgp_level = 0

def allocate_vrf_roles(g_vrf):
    """Allocate VRF roles"""
    g_phy = g_vrf.anm['phy']
    for node in g_vrf.nodes(vrf_role="CE"):
        if not node.vrf:
            node.vrf = "default_vrf"

    for node in g_vrf.nodes('vrf'):
        node.vrf_role = "CE"

    non_ce_nodes = [node for node in g_vrf if node.vrf_role != "CE"]

    for node in non_ce_nodes:
        phy_neighbors = g_phy.node(node).neighbors("is_router")
        # neighbors from physical graph for connectivity
        phy_neighbors = [neigh for neigh in phy_neighbors]
            # filter to just this asn
        if any(g_vrf.node(neigh).vrf_role == "CE" for neigh in phy_neighbors):
            # phy neigh has vrf set in this graph
            node.vrf_role = "PE"
        else:
            node.vrf_role = "P"  # default role

def add_vrf_loopbacks(g_vrf):
    """Adds loopbacks for VRFs, and stores VRFs connected to PE router"""
    for node in g_vrf.nodes(vrf_role="PE"):
        node_vrf_names = {n.vrf for n in node.neighbors(vrf_role="CE")}
        node.node_vrf_names = node_vrf_names
        node.rd_indices = {}
        for index, vrf_name in enumerate(node_vrf_names, 1):
            node.rd_indices[vrf_name] = index
            node.add_loopback(vrf_name=vrf_name,
                              description="loopback for vrf %s" % vrf_name)

def build_ibgp_vpn_v4(anm):
    """Based on the ibgp_v4 hierarchy rules.
    Exceptions:
    1. Remove links to (PE, RRC) nodes

    CE nodes are excluded from RR hierarchy ibgp creation through pre-process step

    """
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    g_bgp = anm['bgp']
    g_ibgp_v4 = anm['ibgp_v4']
    g_vrf = anm['vrf']
    g_ibgp_vpn_v4= anm.add_overlay("ibgp_vpn_v4", directed=True)

    ibgp_v4_nodes = list(g_ibgp_v4.nodes())
    pe_nodes = set(g_vrf.nodes(vrf_role = "PE"))
    pe_rrc_nodes = {n for n in ibgp_v4_nodes if
            n in pe_nodes and n.ibgp_role == "RRC"}
    ce_nodes = set(g_vrf.nodes(vrf_role = "CE"))

    if len(pe_nodes) == len(ce_nodes) == len(pe_rrc_nodes) == 0:
        # no vrf nodes to connect
        return

    #TODO: extend this to only connect nodes which are connected in VRFs, so don't set to others

    ibgp_vpn_v4_nodes = (n for n in ibgp_v4_nodes
            if n not in pe_rrc_nodes and n not in ce_nodes)
    g_ibgp_vpn_v4.add_nodes_from(ibgp_vpn_v4_nodes, retain = "ibgp_level")
    g_ibgp_vpn_v4.add_edges_from(g_ibgp_v4.edges(), retain = "direction")

    for node in g_ibgp_vpn_v4:
        if node.ibgp_level in (2, 3): # HRR or RR
            node.retain_route_target = True

    ce_edges = [e for e in g_ibgp_vpn_v4.edges()
            if e.src in ce_nodes or e.dst in ce_nodes]

    # mark ibgp direction
    ce_pe_edges = []
    pe_ce_edges = []
    for edge in g_ibgp_vpn_v4.edges():
        if (edge.src.vrf_role, edge.dst.vrf_role) == ("CE", "PE"):
            edge.direction = "up"
            edge.vrf = edge.src.vrf
            ce_pe_edges.append(edge)
        elif (edge.src.vrf_role, edge.dst.vrf_role) == ("PE", "CE"):
            edge.direction = "down"
            edge.vrf = edge.dst.vrf
            pe_ce_edges.append(edge)

    #TODO: Document this
    g_ibgpv4 = anm['ibgp_v4']
    g_ibgpv6 = anm['ibgp_v6']
    g_ibgpv4.remove_edges_from(ce_edges)
    g_ibgpv6.remove_edges_from(ce_edges)
    g_ibgpv4.add_edges_from(ce_pe_edges, retain = ["direction", "vrf"])
    g_ibgpv4.add_edges_from(pe_ce_edges, retain = ["direction", "vrf"])
    g_ibgpv6.add_edges_from(ce_pe_edges, retain = ["direction", "vrf"])
    g_ibgpv6.add_edges_from(pe_ce_edges, retain = ["direction", "vrf"])
    for edge in pe_ce_edges:
        # mark as exclude so don't include in standard ibgp config stanzas
        if g_ibgpv4.has_edge(edge):
            edge['ibgp_v4'].exclude = True
        if g_ibgpv6.has_edge(edge):
            edge['ibgp_v6'].exclude = True

# legacy
    g_bgp = anm['bgp']
    g_bgp.remove_edges_from(ce_edges)
    g_bgp.add_edges_from(ce_pe_edges, retain = ["direction", "vrf", "type"])
    g_bgp.add_edges_from(pe_ce_edges, retain = ["direction", "vrf", "type"])

    # also need to modify the ibgp_v4 and ibgp_v6 graphs

def build_mpls_ldp(anm):
    """Builds MPLS LDP"""
    g_in = anm['input']
    g_vrf = anm['vrf']
    g_l3conn = anm['l3_conn']
    g_mpls_ldp = anm.add_overlay("mpls_ldp")
    nodes_to_add = [n for n in g_in.nodes("is_router")
            if n['vrf'].vrf_role in ("PE", "P")]
    g_mpls_ldp.add_nodes_from(nodes_to_add, retain=["vrf_role", "vrf"])

    # store as set for faster lookup
    pe_nodes = set(g_vrf.nodes(vrf_role = "PE"))
    p_nodes = set(g_vrf.nodes(vrf_role = "P"))

    pe_to_pe_edges = (e for e in g_l3conn.edges()
            if e.src in pe_nodes and e.dst in pe_nodes)
    g_mpls_ldp.add_edges_from(pe_to_pe_edges)

    pe_to_p_edges = (e for e in g_l3conn.edges()
            if e.src in pe_nodes and e.dst in p_nodes
            or e.src in p_nodes and e.dst in pe_nodes)
    g_mpls_ldp.add_edges_from(pe_to_p_edges)

    p_to_p_edges = (e for e in g_l3conn.edges()
            if e.src in p_nodes and e.dst in p_nodes)
    g_mpls_ldp.add_edges_from(p_to_p_edges)

def mark_ebgp_vrf(anm):
    g_ebgp = anm['ebgp']
    g_vrf = anm['vrf']
    g_ebgpv4 = anm['ebgp_v4']
    g_ebgpv6 = anm['ebgp_v6']
    pe_nodes = set(g_vrf.nodes(vrf_role = "PE"))
    ce_nodes = set(g_vrf.nodes(vrf_role = "CE"))
    for edge in g_ebgpv4.edges():
        if (edge.src in pe_nodes and edge.dst in ce_nodes):
            # exclude from "regular" ebgp (as put into vrf stanza)
            edge.exclude = True
            edge.vrf = edge.dst['vrf'].vrf

    for edge in g_ebgpv6.edges():
        if (edge.src in pe_nodes and edge.dst in ce_nodes):
             # exclude from "regular" ebgp (as put into vrf stanza)
            edge.exclude = True
            edge.vrf = edge.dst['vrf'].vrf

def build_vrf(anm):
    """Build VRF Overlay"""
    g_in = anm['input']
    g_l3conn = anm['l3_conn']
    g_vrf = anm.add_overlay("vrf")

    if not any(True for n in g_in if n.is_router and n.vrf):
        log.debug("No VRFs set")
        return

    g_vrf.add_nodes_from(g_in.nodes("is_router"), retain=["vrf_role", "vrf"])

    allocate_vrf_roles(g_vrf)

    vrf_pre_process(anm)

    def is_pe_ce_edge(edge):
        src_vrf_role = g_vrf.node(edge.src).vrf_role
        dst_vrf_role = g_vrf.node(edge.dst).vrf_role
        return (src_vrf_role, dst_vrf_role) in (("PE", "CE"), ("CE", "PE"))

    vrf_add_edges = (e for e in g_l3conn.edges()
           if is_pe_ce_edge(e))
    #TODO: should mark as being towards PE or CE
    g_vrf.add_edges_from(vrf_add_edges, retain=['edge_id'])

    def is_pe_p_edge(edge):
        src_vrf_role = g_vrf.node(edge.src).vrf_role
        dst_vrf_role = g_vrf.node(edge.dst).vrf_role
        return (src_vrf_role, dst_vrf_role) in (("PE", "P"), ("P", "PE"))
    vrf_add_edges = (e for e in g_l3conn.edges()
            if is_pe_p_edge(e))
    g_vrf.add_edges_from(vrf_add_edges, retain=['edge_id'])

    build_mpls_ldp(anm)
    # add PE to P edges

    add_vrf_loopbacks(g_vrf)
    # allocate route-targets per AS
    # This could later look at connected components for each ASN
    route_targets = {}
    for asn, devices in ank_utils.groupby("asn", g_vrf.nodes(vrf_role = "PE")):
        asn_vrfs = [d.node_vrf_names for d in devices]
        # flatten list to unique set
        asn_vrfs = set(itertools.chain.from_iterable(asn_vrfs))
        route_targets[asn] = {vrf: "%s:%s" % (asn, index)
                for index, vrf in enumerate(sorted(asn_vrfs), 1)}

    g_vrf.data.route_targets = route_targets

    for node in g_vrf:
        vrf_loopbacks = node.interfaces("is_loopback", "vrf_name")
        for index, interface in enumerate(vrf_loopbacks, start = 101):
            interface.index = index

    for edge in g_vrf.edges():
        # Set the vrf of the edge to be that of the CE device (either src or dst)
        edge.vrf = edge.src.vrf if edge.src.vrf_role is "CE" else edge.dst.vrf

    # map attributes to interfaces
    for edge in g_vrf.edges():
        for interface in edge.interfaces():
            interface.vrf_name = edge.vrf



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

    g_phy.add_edges_from(g_in.edges(type="physical"))
    # TODO: make this automatic if adding to the physical graph?

    if g_in.data.Creator == "Maestro":
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

    g_phy.allocate_interfaces()

    for node in g_phy:
        for interface in node:
            specified_id = interface['input'].get("specified_id")
            if specified_id:
                interface.specified_id = specified_id # map across

    for node in g_phy.nodes("specified_int_names"):
        for interface in node:
            edge = interface.edges()[0]
            directed_edge = anm['input_directed'].edge(edge)
            interface.name = directed_edge.name

def build_l3_connectivity(anm):
    """ creates l3_connectivity graph, which is switch nodes aggregated and exploded"""
    #TODO: use this as base for ospf, ebgp, ip, etc rather than exploding in each
    g_in = anm['input']
    g_l3conn = anm.add_overlay("l3_conn")
    g_l3conn.add_nodes_from(g_in, retain=['label', 'update', 'device_type', 'asn',
        'specified_int_names',
        'device_subtype', 'platform', 'host', 'syntax'])
    g_l3conn.add_nodes_from(g_in.nodes("is_switch"), retain=['asn'])
#TODO: check if edge_id needs to be still retained
    g_l3conn.add_edges_from(g_in.edges(), retain=['edge_id'])

    ank_utils.aggregate_nodes(g_l3conn, g_l3conn.nodes("is_switch"),
                              retain="edge_id")
    exploded_edges = ank_utils.explode_nodes(g_l3conn, g_l3conn.nodes("is_switch"),
                            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True

def build_conn(anm):
    """Build connectivity overlay"""
    g_in = anm['input']
    g_conn = anm.add_overlay("conn", directed=True)
    g_conn.add_nodes_from(g_in, retain=['label'])
    g_conn.add_edges_from(g_in.edges(type="physical"))

    return



