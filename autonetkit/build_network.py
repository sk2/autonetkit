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

__all__ = ['build']

MESSAGING = ank_messaging.AnkMessaging()

def load(input_graph_string):
    try:
        input_graph = graphml.load_graphml(input_graph_string)
    except autonetkit.exception.AnkIncorrectFileFormat:
# try a different reader
        try:
            from autonetkit_cisco import load as cisco_load
        except ImportError:
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
    import networkx as nx
    graph = nx.grid_2d_graph(dim, dim)

    for n in graph:
        graph.node[n]['asn'] = 1
        graph.node[n]['x'] = n[0] * 150
        graph.node[n]['y'] = n[1] * 150
        graph.node[n]['device_type'] = 'router'
        graph.node[n]['platform'] = 'cisco'
        graph.node[n]['syntax'] = 'ios2'
        graph.node[n]['host'] = 'internal'
        graph.node[n]['ibgp_level'] = 0

    mapping = {n: "%s_%s" % (n[0], n[1]) for n in graph}
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
                              'device_subtype', 'pop', 'asn'])

    return anm

def apply_design_rules(anm):
    g_in = anm['input']

    build_phy(anm)
    g_phy = anm['phy']

    build_l3_connectivity(anm)

    build_vrf(anm) # need to do before to add loopbacks before ip allocations
    build_ip(anm) # ip infrastructure topology

#TODO: set defaults at the start, rather than inline, ie set g_in.data.address_family then use later

    address_family = g_in.data.address_family or "v4" # default is v4
#TODO: can remove the infrastructure now create g_ip seperately
    if address_family in ("v4", "dual_stack"):
        build_ipv4(anm, infrastructure = True)
        g_phy.update(g_phy, use_ipv4 = True)
    else:
        build_ipv4(anm, infrastructure = False)

    #TODO: Create a collision domain overlay for ip addressing - l2 overlay?
    if address_family in ("v6", "dual_stack"):
        build_ipv6(anm)
        g_phy.update(g_phy, use_ipv6 = True)
    else:
        anm.add_overlay("ipv6") # placeholder for compiler logic

    default_igp = g_in.data.igp or "ospf" 
    non_igp_nodes = [n for n in g_in if not n.igp]
#TODO: should this be modifying g_in?
    g_in.update(non_igp_nodes, igp=default_igp) # store igp onto each node

    ank_utils.copy_attr_from(g_in, g_phy, "include_csr")

    build_ospf(anm)
    build_isis(anm)
    build_bgp(anm)
    autonetkit.update_http(anm)

# post-processing
    mark_ebgp_vrf(anm)
    build_ibgp_vpn_v4(anm) # build after bgp as is based on
    #autonetkit.update_http(anm)
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
    g_phy = anm['phy']
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
    g_ebgpv4= anm['ebgp_v4']
    g_ebgpv6= anm['ebgp_v6']
    pe_nodes = set(g_vrf.nodes(vrf_role = "PE"))
    ce_nodes = set(g_vrf.nodes(vrf_role = "CE"))
    for edge in g_ebgpv4.edges():
        if (edge.src in pe_nodes and edge.dst in ce_nodes):
            edge.exclude = True # exclude from "regular" ebgp (as put into vrf stanza)
            edge.vrf = edge.dst['vrf'].vrf

    for edge in g_ebgpv6.edges():
        if (edge.src in pe_nodes and edge.dst in ce_nodes):
            edge.exclude = True # exclude from "regular" ebgp (as put into vrf stanza)
            edge.vrf = edge.dst['vrf'].vrf


def build_vrf(anm):
    """Build VRF Overlay"""
    g_in = anm['input']
    g_l3conn = anm['l3_conn']
    g_vrf = anm.add_overlay("vrf")
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

def three_tier_ibgp_corner_cases(rtrs):
    """Calculate edges for iBGP l3 clusters that don't contain a HRR.
    Connects l1 to l3 directly"""
    up_links = []
    down_links = []
    over_links = []
    for l3_cluster, l3d in ank_utils.groupby("ibgp_l3_cluster", rtrs):
        for l2_cluster, l2d in ank_utils.groupby("ibgp_l2_cluster", l3d):
            l2d = list(l2d)
            if any(r.ibgp_level == 2 for r in l2d):
                log.debug("Cluster (%s, %s) has l2 devices, not "
                          "adding extra links" % (l3_cluster, l2_cluster))
            elif all(r.ibgp_level == 1 for r in l2d):
                # No l2 or l3 routers -> full-mesh of l1 routers
                over_links += [(s, t) for s in l2d for t in l2d if s != t]
                log.debug("Cluster (%s, %s) has no level 2 or 3 iBGP routers."
                        "Connecting l1 routers (%s) in full-mesh"
                        % (l3_cluster, l2_cluster, l2d))
            else:
                l1_rtrs = [r for r in l2d if r.ibgp_level == 1]
                l3_rtrs = [r for r in l2d if r.ibgp_level == 3]
                if not(len(l1_rtrs) and len(l3_rtrs)):
                    break  # no routers to connect
                log.debug("Cluster (%s, %s) has no level 2 iBGP routers."
                          "Connecting l1 routers (%s) to l3 routers (%s)"
                          % (l3_cluster, l2_cluster, l1_rtrs, l3_rtrs))

                l1_l3_up_links = [(s, t) for s in l1_rtrs for t in l3_rtrs]
                up_links += l1_l3_up_links
                down_links += [(t, s) for (s, t) in l1_l3_up_links]

    return up_links, down_links, over_links

def three_tier_ibgp_edges(routers):
    """Constructs three-tier ibgp"""
    up_links = []
    down_links = []
    over_links = []
    all_pairs = [(s, t) for s in routers for t in routers if s != t]
    l1_l2_up_links = [(s, t) for (s, t) in all_pairs
                      if (s.ibgp_level, t.ibgp_level) == (1, 2)
                      and s.ibgp_l2_cluster == t.ibgp_l2_cluster
                      and s.ibgp_l3_cluster == t.ibgp_l3_cluster
                      ]
    up_links += l1_l2_up_links
    down_links += [(t, s) for (s, t) in l1_l2_up_links]  # the reverse

    over_links += [(s, t) for (s, t) in all_pairs
                   if s.ibgp_level == t.ibgp_level == 2
                   and s.ibgp_l2_cluster == t.ibgp_l2_cluster
                   and s.ibgp_l3_cluster == t.ibgp_l3_cluster
                   ]  # l2 peer links

    l2_l3_up_links = [(s, t) for (s, t) in all_pairs
                      if (s.ibgp_level, t.ibgp_level) == (2, 3)
                      and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
    up_links += l2_l3_up_links
    down_links += [(t, s) for (s, t) in l2_l3_up_links]  # the reverse

    over_links += [(s, t) for (s, t) in all_pairs
                   if s.ibgp_level == t.ibgp_level == 3]  # l3 peer links

# also check for any clusters which only contain l1 and l3 links
    l1_l3_up_links, l1_l3_down_links, l1_l3_over_links = three_tier_ibgp_corner_cases(routers)
    up_links += l1_l3_up_links
    down_links += l1_l3_down_links
    over_links += l1_l3_over_links
  
    return up_links, down_links, over_links

def build_two_tier_ibgp(routers):
    """Constructs two-tier ibgp"""
    up_links = down_links = over_links = []
    all_pairs = [(s, t) for s in routers for t in routers if s != t]
    up_links = [(s, t) for (s, t) in all_pairs
                if (s.ibgp_level, t.ibgp_level) == (1, 2)
                and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
    down_links = [(t, s) for (s, t) in up_links]  # the reverse

    over_links = [(s, t) for (s, t) in all_pairs
                  if s.ibgp_level == t.ibgp_level == 2
                  and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
    return up_links, down_links, over_links

def build_ibgp_v4(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    #TODO: base on generic ibgp graph, rather than bgp graph
    g_bgp = anm['bgp']
    g_phy = anm['phy']
    g_ibgpv4 = anm.add_overlay("ibgp_v4", directed=True)
    ipv4_nodes = set(g_phy.nodes("is_router", "use_ipv4"))
    g_ibgpv4.add_nodes_from((n for n in g_bgp if n in ipv4_nodes),
            retain = ["ibgp_level", "ibgp_l2_cluster", "ibgp_l3_cluster"] )
    g_ibgpv4.add_edges_from(g_bgp.edges(type="ibgp"), retain="direction")

def build_ibgp_v6(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    #TODO: base on generic ibgp graph, rather than bgp graph
    g_bgp = anm['bgp']
    g_phy = anm['phy']
    g_ibgpv6 = anm.add_overlay("ibgp_v6", directed=True)
    ipv6_nodes = set(g_phy.nodes("is_router", "use_ipv6"))
    g_ibgpv6.add_nodes_from((n for n in g_bgp if n in ipv6_nodes),
            retain = ["ibgp_level", "ibgp_l2_cluster", "ibgp_l3_cluster"] )
    g_ibgpv6.add_edges_from(g_bgp.edges(type="ibgp"), retain="direction")

def build_ebgp_v4(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    g_ebgp = anm['ebgp']
    g_phy = anm['phy']
    g_ebgpv4 = anm.add_overlay("ebgp_v4", directed=True)
    ipv4_nodes = set(g_phy.nodes("is_router", "use_ipv4"))
    g_ebgpv4.add_nodes_from(n for n in g_ebgp if n in ipv4_nodes)
    g_ebgpv4.add_edges_from(g_ebgp.edges(), retain="direction")

def build_ebgp_v6(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    g_ebgp = anm['ebgp']
    g_phy = anm['phy']
    g_ebgpv6 = anm.add_overlay("ebgp_v6", directed=True)
    ipv6_nodes = set(g_phy.nodes("is_router", "use_ipv6"))
    g_ebgpv6.add_nodes_from(n for n in g_ebgp if n in ipv6_nodes)
    g_ebgpv6.add_edges_from(g_ebgp.edges(), retain="direction")

def build_ebgp(anm):
    g_in = anm['input']
    g_phy = anm['phy']
    g_ebgp = anm.add_overlay("ebgp", directed=True)
    g_ebgp.add_nodes_from(g_in.nodes("is_router"))
    ebgp_edges = [e for e in g_in.edges() if not e.attr_equal("asn")]
    g_ebgp.add_edges_from(ebgp_edges, bidirectional=True, type='ebgp')

    ebgp_switches = [n for n in g_in.nodes("is_switch")
            if not ank_utils.neigh_equal(g_phy, n, "asn")]
    g_ebgp.add_nodes_from(ebgp_switches, retain=['asn'])
    log.debug("eBGP switches are %s" % ebgp_switches)
    g_ebgp.add_edges_from((e for e in g_in.edges()
            if e.src in ebgp_switches or e.dst in ebgp_switches), bidirectional=True, type='ebgp')
    ank_utils.aggregate_nodes(g_ebgp, ebgp_switches, retain="edge_id")
    ebgp_switches = list(g_ebgp.nodes("is_switch")) # need to recalculate as may have aggregated
    log.debug("aggregated eBGP switches are %s" % ebgp_switches)
    exploded_edges = ank_utils.explode_nodes(g_ebgp, ebgp_switches,
            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True

def build_bgp(anm):
    """Build iBGP end eBGP overlays"""
    # eBGP
    g_in = anm['input']
    g_phy = anm['phy']

    build_ebgp(anm)
    build_ebgp_v4(anm)
    build_ebgp_v6(anm)

    """TODO: remove from here once compiler updated"""
    g_bgp = anm.add_overlay("bgp", directed=True)
    g_bgp.add_nodes_from(g_in.nodes("is_router"))
    ebgp_edges = [edge for edge in g_in.edges() if not edge.attr_equal("asn")]
    g_bgp.add_edges_from(ebgp_edges, bidirectional=True, type='ebgp')
#TODO: why don't we include edge_id here

    ebgp_switches = [n for n in g_in.nodes("is_switch")
            if not ank_utils.neigh_equal(g_phy, n, "asn")]
    g_bgp.add_nodes_from(ebgp_switches, retain=['asn'])
    log.debug("eBGP switches are %s" % ebgp_switches)
    g_bgp.add_edges_from((e for e in g_in.edges()
            if e.src in ebgp_switches or e.dst in ebgp_switches), bidirectional=True, type='ebgp')
    ank_utils.aggregate_nodes(g_bgp, ebgp_switches, retain="edge_id")
    ebgp_switches = list(g_bgp.nodes("is_switch")) # need to recalculate as may have aggregated
    log.debug("aggregated eBGP switches are %s" % ebgp_switches)
    exploded_edges = ank_utils.explode_nodes(g_bgp, ebgp_switches,
            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True
    """TODO: remove up to here once compiler updated"""

# now iBGP
    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_level")
    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_l2_cluster")
    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_l3_cluster")
    for node in g_bgp:
        # set defaults
        if node.ibgp_level is None:
            node.ibgp_level = 1

        if node.ibgp_level == "None":  # if unicode string from yEd
            node.ibgp_level = 1

#TODO CHECK FOR IBGP NONE

        node.ibgp_level = int(node.ibgp_level)  # ensure is numeric

        if not node.ibgp_l2_cluster or node.ibgp_l2_cluster == "None":
            # ibgp_l2_cluster defaults to region
            node.ibgp_l2_cluster = node.region or "default_l2_cluster"
        if not node.ibgp_l3_cluster or node.ibgp_l3_cluster == "None":
            # ibgp_l3_cluster defaults to ASN
            node.ibgp_l3_cluster = node.asn

    for asn, devices in ank_utils.groupby("asn", g_bgp):
        # group by nodes in phy graph
        routers = list(g_bgp.node(n) for n in devices if n.is_router)
        # list of nodes from bgp graph
        ibgp_levels = {int(r.ibgp_level) for r in routers}
        max_level = max(ibgp_levels)
        # all possible edge src/dst pairs
        ibgp_routers = [r for r in routers if r.ibgp_level > 0]
        all_pairs = [(s, t) for s in ibgp_routers for t in ibgp_routers if s != t]
        if max_level == 3:
            up_links, down_links, over_links = three_tier_ibgp_edges(ibgp_routers)

        elif max_level == 2:
            up_links, down_links, over_links = build_two_tier_ibgp(ibgp_routers)

        elif max_level == 1:
            up_links = []
            down_links = []
            over_links = [(s, t) for (s, t) in all_pairs
                             if s.ibgp_l3_cluster == t.ibgp_l3_cluster
                             and s.ibgp_l2_cluster == t.ibgp_l2_cluster
                             ]
        else:
            # no iBGP
            up_links = []
            down_links = []
            over_links = []

        if max_level > 0:
            g_bgp.add_edges_from(up_links, type='ibgp', direction='up')
            g_bgp.add_edges_from(down_links, type='ibgp', direction='down')
            g_bgp.add_edges_from(over_links, type='ibgp', direction='over')

        else:
            log.debug("No iBGP routers in %s" % asn)

# and set label back
    ibgp_label_to_level = {
        0: "None",  # Explicitly set role to "None" -> Not in iBGP
        3: "RR",
        1: "RRC",
        2: "HRR",
    }
    for node in g_bgp:
        node.ibgp_role = ibgp_label_to_level[node.ibgp_level]

    ebgp_nodes = [d for d in g_bgp if any(
        edge.type == 'ebgp' for edge in d.edges())]
    g_bgp.update(ebgp_nodes, ebgp=True)

    for ebgp_edge in g_bgp.edges(type = "ebgp"):
        for interface in ebgp_edge.interfaces():
            interface.ebgp = True

    for edge in g_bgp.edges(type='ibgp'):
        # TODO: need interface querying/selection. rather than hard-coded ids
        edge.bind_interface(edge.src, 0)

    #TODO: need to initialise interface zero to be a loopback rather than physical type
    for node in g_bgp:
        for interface in node.interfaces():
            interface.multipoint = any(e.multipoint for e in interface.edges())

    build_ibgp_v4(anm)
    build_ibgp_v6(anm)

def build_ipv6(anm):
    """Builds IPv6 graph, using nodes and edges from IPv4 graph"""
    import autonetkit.plugins.ipv6 as ipv6
    # uses the nodes and edges from ipv4
    g_ipv6 = anm.add_overlay("ipv6")
    g_ip = anm['ip']
    g_ipv6.add_nodes_from(
        g_ip, retain="collision_domain")  # retain if collision domain or not
    g_ipv6.add_edges_from(g_ip.edges())

    ipv6.allocate_ips(g_ipv6)

    #TODO: replace this with direct allocation to interfaces in ip alloc plugin
    for node in g_ipv6.nodes("is_l3device"):
        node.loopback_zero.ip_address = node.loopback
        for interface in node:
            edges = list(interface.edges())
            if len(edges):
                edge = edges[0] # first (only) edge
                interface.ip_address = edge.ip #TODO: make this consistent
                interface.subnet = edge.dst.subnet # from collision domain

def manual_ipv4_infrastructure_allocation(anm):
    """Applies manual IPv4 allocation"""
    import netaddr
    g_in_directed = anm['input_directed']
    g_ipv4 = anm['ipv4']
    #TODO: tidy this up to work with interfaces directly

    for l3_device in g_ipv4.nodes("is_l3device"):
        for edge in l3_device.edges():
            # find edge in g_in_directed
            directed_edge = g_in_directed.edge(edge)
            edge.ip_address = netaddr.IPAddress(directed_edge.ipv4)

            # set subnet onto collision domain (can come from either
            # direction)
            collision_domain = edge.dst
            if not collision_domain.subnet:
                # TODO: see if direct method in netaddr to deduce network
                prefixlen = directed_edge.netPrefixLenV4
                cidr_string = "%s/%s" % (edge.ip_address, prefixlen)

                intermediate_subnet = netaddr.IPNetwork(cidr_string)
                cidr_string = "%s/%s" % (
                    intermediate_subnet.network, prefixlen)
                subnet = netaddr.IPNetwork(cidr_string)
                collision_domain.subnet = subnet

    #TODO: assign directly to interfaces

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)
    infra_blocks = {}
    for asn, devices in g_ipv4.groupby("asn").items():
        collision_domains = [d for d in devices if d.collision_domain]
        subnets = [cd.subnet for cd in collision_domains]
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    g_ipv4.data.infra_blocks = infra_blocks

def manual_ipv4_loopback_allocation(anm):
    """Applies manual IPv4 allocation"""
    import netaddr
    g_in_directed = anm['input_directed']
    g_ipv4 = anm['ipv4']

    for l3_device in g_ipv4.nodes("is_l3device"):
        directed_node = g_in_directed.node(l3_device)
        l3_device.loopback = directed_node.ipv4loopback

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)
    loopback_blocks = {}
    for asn, devices in g_ipv4.groupby("asn").items():
        routers = [d for d in devices if d.is_router]
        loopbacks = [r.loopback for r in routers]
        loopback_blocks[asn] = netaddr.cidr_merge(loopbacks)

    g_ipv4.data.loopback_blocks = loopback_blocks

def build_ip(anm):
    g_ip = anm.add_overlay("ip")
    g_in = anm['input']
    g_graphics = anm['graphics']
    g_phy = anm['phy']

    g_ip.add_nodes_from(g_in)
    g_ip.add_edges_from(g_in.edges(type="physical"))

    ank_utils.aggregate_nodes(g_ip, g_ip.nodes("is_switch"),
                              retain="edge_id")

    edges_to_split = [edge for edge in g_ip.edges() if edge.attr_both(
        "is_l3device")]
    for edge in edges_to_split:
        edge.split = True # mark as split for use in building nidb
    split_created_nodes = list(
        ank_utils.split(g_ip, edges_to_split, retain=['edge_id', 'split'], id_prepend = "cd"))
    for node in split_created_nodes:
        node['graphics'].x = ank_utils.neigh_average(g_ip, node, "x",
                                                     g_graphics) + 0.1 # temporary fix for gh-90
        node['graphics'].y = ank_utils.neigh_average(g_ip, node, "y",
                                                     g_graphics) + 0.1 # temporary fix for gh-90
        asn = ank_utils.neigh_most_frequent(
            g_ip, node, "asn", g_phy)  # arbitrary choice
        node['graphics'].asn = asn
        node.asn = asn # need to use asn in IP overlay for aggregating subnets

    switch_nodes = g_ip.nodes("is_switch")  # regenerate due to aggregated
    g_ip.update(switch_nodes, collision_domain=True)
                 # switches are part of collision domain
    g_ip.update(split_created_nodes, collision_domain=True)
# Assign collision domain to a host if all neighbours from same host
    for node in split_created_nodes:
        if ank_utils.neigh_equal(g_ip, node, "host", g_phy):
            node.host = ank_utils.neigh_attr(
                g_ip, node, "host", g_phy).next()  # first attribute

# set collision domain IPs
    for node in g_ip.nodes("collision_domain"):
        graphics_node = g_graphics.node(node)
        graphics_node.device_type = "collision_domain"
        if not node.is_switch:
            # use node sorting, as accomodates for numeric/string names
            neighbors = sorted(neigh for neigh in node.neighbors())
            label = "_".join(neigh.label for neigh in neighbors) 
            cd_label = "cd_%s" % label  # switches keep their names
            node.label = cd_label
            node.cd_id = cd_label
            graphics_node.label = cd_label

def extract_ipv4_blocks(anm):
    #TODO: set all these blocks globally in config file, rather than repeated in load, build_network, compile, etc
    from autonetkit.ank import sn_preflen_to_network
    from netaddr import IPNetwork
    g_in = anm['input']

    try:
        infra_subnet = g_in.data.ipv4_infra_subnet
        infra_prefix = g_in.data.ipv4_infra_prefix
        infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        log.debug("Unable to obtain infra_subnet from input graph: %s" % e)
        infra_block = IPNetwork("10.0.0.0/8")

    try:
        loopback_subnet = g_in.data.ipv4_loopback_subnet
        loopback_prefix = g_in.data.ipv4_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet, loopback_prefix)
    except Exception, e:
        log.debug("Unable to obtain loopback_subnet from input graph: %s" % e)
        loopback_block = IPNetwork("10.0.0.0/8")

    try:
        vrf_loopback_subnet = g_in.data.ipv4_vrf_loopback_subnet
        vrf_loopback_prefix = g_in.data.ipv4_vrf_loopback_prefix
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet, vrf_loopback_prefix)
    except Exception, e:
        log.debug("Unable to obtain vrf_loopback_subnet from input graph: %s" % e)
        vrf_loopback_block = IPNetwork("172.16.0.0/24")

    return infra_block, loopback_block, vrf_loopback_block

def build_ipv4(anm, infrastructure=True):
    """Builds IPv4 graph"""
    import autonetkit.plugins.ipv4 as ipv4
    g_ipv4 = anm.add_overlay("ipv4")
    g_ip = anm['ip']
    g_in = anm['input']
    g_ipv4.add_nodes_from(
        g_ip, retain="collision_domain")  # retain if collision domain or not
    # Copy ASN attribute chosen for collision domains (used in alloc algorithm)
    ank_utils.copy_attr_from(g_ip, g_ipv4, "asn", nbunch = g_ipv4.nodes("collision_domain"))
    g_ipv4.add_edges_from(g_ip.edges())

    # check if ip ranges have been specified on g_in
    infra_block, loopback_block, vrf_loopback_block = extract_ipv4_blocks(anm)

    #TODO: need to set allocate_ipv4 by default in the readers
    if g_in.data.alloc_ipv4_infrastructure is False:
        manual_ipv4_infrastructure_allocation(anm)
    else:
        ipv4.allocate_infra(g_ipv4, infra_block)

    if g_in.data.alloc_ipv4_loopbacks is False:
        manual_ipv4_loopback_allocation(anm)
    else:
        ipv4.allocate_loopbacks(g_ipv4, loopback_block)

    #TODO: need to also support secondary_loopbacks for IPv6
    ipv4.allocate_vrf_loopbacks(g_ipv4, vrf_loopback_block)

    #TODO: replace this with direct allocation to interfaces in ip alloc plugin
    for node in g_ipv4.nodes("is_l3device"):
        node.loopback_zero.ip_address = node.loopback
        for interface in node:
            edges = list(interface.edges())
            if len(edges):
                edge = edges[0] # first (only) edge
                interface.ip_address = edge.ip_address
                interface.subnet = edge.dst.subnet # from collision domain

    # TODO: also map loopbacks to loopback interface 0

def build_phy(anm):
    """Build physical overlay"""
    g_in = anm['input']
    g_phy = anm['phy']

    # apply uuid if not set
    g_phy.data.uuid = g_phy.data.uuid
    if not g_phy.data.uuid:
        import uuid
        g_phy.data.uuid = uuid.uuid4().hex[:10]

    g_phy.add_nodes_from(g_in, retain=['label', 'update', 'device_type', 'asn',
        'specified_int_names',
        'device_subtype', 'platform', 'host', 'syntax'])
    if g_in.data.Creator == "Topology Zoo Toolset":
        ank_utils.copy_attr_from(g_in, g_phy, "Network")

    g_phy.add_edges_from(g_in.edges(type="physical"))
    # TODO: make this automatic if adding to the physical graph?
    g_phy.allocate_interfaces() 

    if g_in.data.Creator == "Maestro":
        g_phy.data.mgmt_interfaces_enabled = g_in.data.mgmt_interfaces_enabled 
        g_phy.data.mgmt_address_start = g_in.data.mgmt_address_start 
        g_phy.data.mgmt_address_end = g_in.data.mgmt_address_end 
        g_phy.data.mgmt_prefixlen = g_in.data.mgmt_prefixlen
        ank_utils.copy_attr_from(g_in, g_phy, "use_cdp")
        ank_utils.copy_attr_from(g_in, g_phy, "use_onepk")

            # copy over numeric interface ids
        for node in g_phy:
            for interface in node:
                edge = interface.edges()[0]
                directed_edge = anm['input_directed'].edge(edge)
                interface.numeric_int_id = directed_edge.numeric_int_id

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

def build_ospf(anm):
    """
    Build OSPF graph.

    Allowable area combinations:
    0 -> 0
    0 -> x (x!= 0)
    x -> 0 (x!= 0)
    x -> x (x != 0)

    Not-allowed:
    x -> x (x != y != 0)

    #TODO: build check that verifies these rules
    """
    import netaddr
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['ospf'] in compilers
    g_ospf = anm.add_overlay("ospf")

    if not any(n.igp == "ospf" for n in g_in):
        log.debug("No OSPF nodes")
        return

    g_ospf.add_nodes_from(g_in.nodes("is_router", igp = "ospf"), retain=['asn'])
    g_ospf.add_nodes_from(g_in.nodes("is_server", igp = "ospf"), retain=['asn'])
    g_ospf.add_nodes_from(g_in.nodes("is_switch"), retain=['asn'])
    g_ospf.add_edges_from(g_in.edges(), retain=['edge_id'])

    ank_utils.copy_attr_from(g_in, g_ospf, "ospf_area", dst_attr="area")
    ank_utils.copy_edge_attr_from(g_in, g_ospf, "ospf_cost", dst_attr="cost",  type=float)

    ank_utils.aggregate_nodes(g_ospf, g_ospf.nodes("is_switch"),
                              retain="edge_id")
    exploded_edges = ank_utils.explode_nodes(g_ospf, g_ospf.nodes("is_switch"),
                            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True

    g_ospf.remove_edges_from([link for link in g_ospf.edges(
    ) if link.src.asn != link.dst.asn])  # remove inter-AS links

    area_zero_ip = netaddr.IPAddress("0.0.0.0")
    area_zero_int = 0
    area_zero_ids = {area_zero_ip, area_zero_int}
    default_area = area_zero_int
    if any(router.area == "0.0.0.0" for router in g_ospf):
        # string comparison as hasn't yet been cast to IPAddress
        default_area = area_zero_ip

    for router in g_ospf:
        if not router.area or router.area == "None":
            router.area = default_area
            # check if 0.0.0.0 used anywhere, if so then use 0.0.0.0 as format
        else:
            try:
                router.area = int(router.area)
            except ValueError:
                try:
                    router.area = netaddr.IPAddress(router.area)
                except netaddr.core.AddrFormatError:
                    log.warning("Invalid OSPF area %s for %s. Using default"
                                " of %s" % (router.area, router, default_area))
                    router.area = default_area

    for router in g_ospf:
# and set area on interface
        for edge in router.edges():
            if edge.area:
                continue  # allocated (from other "direction", as undirected)
            if router.area == edge.dst.area:
                edge.area = router.area  # intra-area
                continue

            if router.area in area_zero_ids or edge.dst.area in area_zero_ids:
# backbone to other area
                if router.area in area_zero_ids:
                    # router in backbone, use other area
                    edge.area = edge.dst.area
                else:
                    # router not in backbone, use its area
                    edge.area = router.area

    for router in g_ospf:
        areas = {edge.area for edge in router.edges()}
        router.areas = list(areas)  # edges router participates in

        if len(areas) in area_zero_ids:
            router.type = "backbone"  # no ospf edges (eg single node in AS)
        elif len(areas) == 1:
            # single area: either backbone (all 0) or internal (all nonzero)
            if len(areas & area_zero_ids):
                # intersection has at least one element -> router has area zero
                router.type = "backbone"
            else:
                router.type = "internal"

        else:
            # multiple areas
            if len(areas & area_zero_ids):
                # intersection has at least one element -> router has area zero
                router.type = "backbone ABR"
            else:
                log.warning(
                    "%s spans multiple areas but is not a member of area 0"
                    % router)
                router.type = "INVALID"

    if (any(area_zero_int in router.areas for router in g_ospf) and
            any(area_zero_ip in router.areas for router in g_ospf)):
        log.warning("Using both area 0 and area 0.0.0.0")

    for link in g_ospf.edges():
        if not link.cost:
            link.cost = 1

    # map areas and costs onto interfaces
    #TODO: later map them directly rather than with edges - this is part of the transition
    for edge in g_ospf.edges():
        for interface in edge.interfaces():
            interface.cost = edge.cost
            interface.area = edge.area
            interface.multipoint = edge.multipoint

    for router in g_ospf:
        router.loopback_zero.area = router.area
        router.loopback_zero.cost = 0

def ip_to_net_ent_title_ios(ip_addr):
    """ Converts an IP address into an OSI Network Entity Title
    suitable for use in IS-IS on IOS.

    >>> ip_to_net_ent_title_ios(IPAddress("192.168.19.1"))
    '49.1921.6801.9001.00'
    """
    try:
        ip_words = ip_addr.words
    except AttributeError:
        import netaddr  # try to cast to IP Address
        ip_addr = netaddr.IPAddress(ip_addr)
        ip_words = ip_addr.words

    log.debug("Converting IP to OSI ENT format")
    area_id = "49"
    ip_octets = "".join("%03d" % int(
        octet) for octet in ip_words)  # single string, padded if needed
    return ".".join([area_id, ip_octets[0:4], ip_octets[4:8], ip_octets[8:12],
                     "00"])


def build_isis(anm):
    """Build isis overlay"""
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['isis'] in compilers
    g_isis = anm.add_overlay("isis") 

    if not any(n.igp == "isis" for n in g_in):
        log.debug("No ISIS nodes")
        return
    g_ipv4 = anm['ipv4']
    g_isis.add_nodes_from(g_in.nodes("is_router", igp = "isis"), retain=['asn'])
    g_isis.add_nodes_from(g_in.nodes("is_server", igp = "isis"), retain=['asn'])
    g_isis.add_nodes_from(g_in.nodes("is_switch"), retain=['asn'])
    g_isis.add_edges_from(g_in.edges(), retain=['edge_id'])
# Merge and explode switches
    ank_utils.aggregate_nodes(g_isis, g_isis.nodes("is_switch"),
                              retain="edge_id")
    exploded_edges = ank_utils.explode_nodes(g_isis, g_isis.nodes("is_switch"),
                            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True

    g_isis.remove_edges_from(
        [link for link in g_isis.edges() if link.src.asn != link.dst.asn])

    for node in g_isis:
        ip_node = g_ipv4.node(node)
        node.net = ip_to_net_ent_title_ios(ip_node.loopback)
        node.process_id = 1  # default

    for link in g_isis.edges():
        link.metric = 1  # default
        # link.hello = 5 # for debugging, TODO: read from graph


    for edge in g_isis.edges():
        for interface in edge.interfaces():
            interface.metric = edge.metric
            interface.multipoint = edge.multipoint

def update_messaging(anm):
    """Sends ANM to web server"""
    log.debug("Sending anm to messaging")
    body = autonetkit.ank_json.dumps(anm, None)
    MESSAGING.publish_compressed("www", "client", body)
