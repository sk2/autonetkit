    #!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.log as log
import autonetkit.ank as ank_utils

import itertools
from autonetkit.ank_utils import call_log

#@call_log


def mpls_te(anm):
    g_in = anm['input']
    g_phy = anm['phy']
    g_l3 = anm['layer3']

    # add regardless, so allows quick check of node in anm['mpls_te'] in
    # compilers

    g_mpls_te = anm.add_overlay('mpls_te')
    if not any(True for n in g_in.routers() if n.mpls_te_enabled):
        log.debug('No nodes with mpls_te_enabled set')
        return

    # te head end set if here

    g_mpls_te.add_nodes_from(g_in.routers())

    # build up edge list sequentially, to provide meaningful messages for
    # multipoint links

    multipoint_edges = [e for e in g_l3.edges() if e.multipoint]
    if len(multipoint_edges):
        log.info('Excluding multi-point edges from MPLS TE topology: %s'
                 % ', '.join(str(e) for e in multipoint_edges))

    edges_to_add = set(g_l3.edges()) - set(multipoint_edges)
    g_mpls_te.add_edges_from(edges_to_add)


#@call_log
def mpls_oam(anm):
    g_in = anm['input']

    # create placeholder graph (may have been created in other steps)

    if anm.has_overlay('mpls_oam'):
        g_mpls_oam = anm['mpls_oam']
    else:
        g_mpls_oam = anm.add_overlay('mpls_oam')

    use_mpls_oam = g_in.data.use_mpls_oam
    if use_mpls_oam:
        g_mpls_oam.add_nodes_from(g_in.routers())

#@call_log


def vrf_pre_process(anm):
    """Marks nodes in g_in as appropriate based on vrf roles.
    CE nodes -> ibgp_role = Disabled, so not in iBGP (this is allocated later)
    """
    log.debug("Applying VRF pre-processing")
    g_vrf = anm['vrf']
    for node in g_vrf.nodes(vrf_role="CE"):
        log.debug("Marking CE node %s as non-ibgp" % node)
        node['input'].ibgp_role = "Disabled"

#@call_log


def allocate_vrf_roles(g_vrf):
    """Allocate VRF roles"""
    g_phy = g_vrf.anm['phy']
    # TODO: might be clearer like ibgp with is_p is_pe etc booleans?  - final
    # step to translate to role for vis
    for node in g_vrf.nodes(vrf_role="CE"):
        if not node.vrf:
            node.vrf = "default_vrf"

    ce_set_nodes = []
    for node in sorted(g_vrf.nodes('vrf')):
        node.vrf_role = "CE"
        ce_set_nodes.append(node)
    if len(ce_set_nodes):
        message = ", ".join(str(n) for n in sorted(ce_set_nodes))
        g_vrf.log.info("VRF role set to CE for %s" % message)

    non_ce_nodes = [node for node in g_vrf if node.vrf_role != "CE"]

    pe_set_nodes = []
    p_set_nodes = []
    for node in sorted(non_ce_nodes):
        phy_neighbors = [
            n for n in g_phy.node(node).neighbors() if n.is_router()]
        # neighbors from physical graph for connectivity
        # TODO: does this do anything?
        phy_neighbors = [neigh for neigh in phy_neighbors]
        # filter to just this asn
        if any(g_vrf.node(neigh).vrf_role == "CE" for neigh in phy_neighbors):
            # phy neigh has vrf set in this graph
            node.vrf_role = "PE"
            pe_set_nodes.append(node)
        else:
            node.vrf_role = "P"  # default role
            p_set_nodes.append(node)

    if len(pe_set_nodes):
        message = ", ".join(str(n) for n in sorted(pe_set_nodes))
        g_vrf.log.info("VRF role set to PE for %s" % message)
    if len(p_set_nodes):
        message = ", ".join(str(n) for n in sorted(p_set_nodes))
        g_vrf.log.info("VRF role set to P for %s" % message)

#@call_log


def add_vrf_loopbacks(g_vrf):
    """Adds loopbacks for VRFs, and stores VRFs connected to PE router"""
    # autonetkit.update_vis(anm)
    for node in g_vrf.nodes(vrf_role="PE"):
        node_vrf_names = {n.vrf for n in node.neighbors(vrf_role="CE")}
        node.node_vrf_names = node_vrf_names
        node.rd_indices = {}
        for index, vrf_name in enumerate(node_vrf_names, 1):
            node.rd_indices[vrf_name] = index
            node.add_loopback(vrf_name=vrf_name,
                              description="loopback for vrf %s" % vrf_name)

#@call_log


def build_ibgp_vpn_v4(anm):
    """Based on the ibgp_v4 hierarchy rules.
    Exceptions:
    1. Remove links to (PE, RRC) nodes

    CE nodes are excluded from RR hierarchy ibgp creation through pre-process step

    """
    # TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in
    # bgp layer
    g_bgp = anm['bgp']
    g_ibgp_v4 = anm['ibgp_v4']
    g_vrf = anm['vrf']
    g_ibgp_vpn_v4 = anm.add_overlay("ibgp_vpn_v4", directed=True)

    v6_vrf_nodes = [n for n in g_vrf
                    if n.vrf is not None and n['phy'].use_ipv6 is True]
    if len(v6_vrf_nodes):
        message = ", ".join(str(s) for s in v6_vrf_nodes)
        log.warning("This version of AutoNetkit does not support IPv6 MPLS VPNs. "
                    "The following nodes have IPv6 enabled but will not have an associated IPv6 MPLS VPN topology created: %s" % message)

    ibgp_v4_nodes = list(g_ibgp_v4.nodes())
    pe_nodes = set(g_vrf.nodes(vrf_role="PE"))
    pe_rrc_nodes = {n for n in ibgp_v4_nodes if
                    n in pe_nodes and n.ibgp_role == "RRC"}
    # TODO: warn if pe_rrc_nodes?
    ce_nodes = set(g_vrf.nodes(vrf_role="CE"))

    if len(pe_nodes) == len(ce_nodes) == len(pe_rrc_nodes) == 0:
        # no vrf nodes to connect
        return

    # TODO: extend this to only connect nodes which are connected in VRFs, so
    # don't set to others

    ibgp_vpn_v4_nodes = (n for n in ibgp_v4_nodes
                         if n not in ce_nodes)
    g_ibgp_vpn_v4.add_nodes_from(ibgp_vpn_v4_nodes, retain=["ibgp_role"])
    g_ibgp_vpn_v4.add_edges_from(g_ibgp_v4.edges(), retain="direction")

    for node in g_ibgp_vpn_v4:
        if node.ibgp_role in ("HRR", "RR"):
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

    # TODO: Document this
    g_ibgpv4 = anm['ibgp_v4']
    g_ibgpv6 = anm['ibgp_v6']
    g_ibgpv4.remove_edges_from(ce_edges)
    g_ibgpv6.remove_edges_from(ce_edges)
    g_ibgpv4.add_edges_from(ce_pe_edges, retain=["direction", "vrf"])
    g_ibgpv4.add_edges_from(pe_ce_edges, retain=["direction", "vrf"])
    g_ibgpv6.add_edges_from(ce_pe_edges, retain=["direction", "vrf"])
    g_ibgpv6.add_edges_from(pe_ce_edges, retain=["direction", "vrf"])
    for edge in pe_ce_edges:
        # mark as exclude so don't include in standard ibgp config stanzas
        if g_ibgpv4.has_edge(edge):
            edge['ibgp_v4'].exclude = True
        if g_ibgpv6.has_edge(edge):
            edge['ibgp_v6'].exclude = True

# legacy
    g_bgp = anm['bgp']
    g_bgp.remove_edges_from(ce_edges)
    g_bgp.add_edges_from(ce_pe_edges, retain=["direction", "vrf", "type"])
    g_bgp.add_edges_from(pe_ce_edges, retain=["direction", "vrf", "type"])

    # also need to modify the ibgp_v4 and ibgp_v6 graphs

#@call_log


def build_mpls_ldp(anm):
    """Builds MPLS LDP"""
    g_in = anm['input']
    g_vrf = anm['vrf']
    g_layer3 = anm['layer3']
    g_mpls_ldp = anm.add_overlay("mpls_ldp")
    nodes_to_add = [n for n in g_in.routers()
                    if n['vrf'].vrf_role in ("PE", "P")]
    g_mpls_ldp.add_nodes_from(nodes_to_add, retain=["vrf_role", "vrf"])

    # store as set for faster lookup
    pe_nodes = set(g_vrf.nodes(vrf_role="PE"))
    p_nodes = set(g_vrf.nodes(vrf_role="P"))

    pe_to_pe_edges = (e for e in g_layer3.edges()
                      if e.src in pe_nodes and e.dst in pe_nodes)
    g_mpls_ldp.add_edges_from(pe_to_pe_edges)

    pe_to_p_edges = (e for e in g_layer3.edges()
                     if e.src in pe_nodes and e.dst in p_nodes
                     or e.src in p_nodes and e.dst in pe_nodes)
    g_mpls_ldp.add_edges_from(pe_to_p_edges)

    p_to_p_edges = (e for e in g_layer3.edges()
                    if e.src in p_nodes and e.dst in p_nodes)
    g_mpls_ldp.add_edges_from(p_to_p_edges)

#@call_log


def mark_ebgp_vrf(anm):
    g_vrf = anm['vrf']
    g_ebgpv4 = anm['ebgp_v4']
    g_ebgpv6 = anm['ebgp_v6']
    pe_nodes = set(g_vrf.nodes(vrf_role="PE"))
    ce_nodes = set(g_vrf.nodes(vrf_role="CE"))
    for edge in g_ebgpv4.edges():
        if edge.src in pe_nodes and edge.dst in ce_nodes:
            # exclude from "regular" ebgp (as put into vrf stanza)
            edge.exclude = True
            edge.vrf = edge.dst['vrf'].vrf

    for edge in g_ebgpv6.edges():
        if edge.src in pe_nodes and edge.dst in ce_nodes:
             # exclude from "regular" ebgp (as put into vrf stanza)
            edge.exclude = True
            edge.vrf = edge.dst['vrf'].vrf

#@call_log


def build_vrf(anm):
    """Build VRF Overlay"""
    g_in = anm['input']
    g_layer3 = anm['layer3']
    g_vrf = anm.add_overlay("vrf")

    import autonetkit
    autonetkit.ank.set_node_default(g_in, vrf=None)

    if not any(True for n in g_in.routers() if n.vrf):
        log.debug("No VRFs set")
        return

    g_vrf.add_nodes_from(g_in.routers(), retain=["vrf_role", "vrf"])

    allocate_vrf_roles(g_vrf)
    vrf_pre_process(anm)

    def is_pe_ce_edge(edge):
        if not(edge.src in g_vrf and edge.dst in g_vrf):
            return False

        src_vrf_role = g_vrf.node(edge.src).vrf_role
        dst_vrf_role = g_vrf.node(edge.dst).vrf_role
        return (src_vrf_role, dst_vrf_role) in (("PE", "CE"), ("CE", "PE"))

    vrf_add_edges = (e for e in g_layer3.edges()
                     if is_pe_ce_edge(e))
    # TODO: should mark as being towards PE or CE
    g_vrf.add_edges_from(vrf_add_edges)

    def is_pe_p_edge(edge):
        if not(edge.src in g_vrf and edge.dst in g_vrf):
            return False
        src_vrf_role = g_vrf.node(edge.src).vrf_role
        dst_vrf_role = g_vrf.node(edge.dst).vrf_role
        return (src_vrf_role, dst_vrf_role) in (("PE", "P"), ("P", "PE"))
    vrf_add_edges = (e for e in g_layer3.edges()
                     if is_pe_p_edge(e))
    g_vrf.add_edges_from(vrf_add_edges)

    build_mpls_ldp(anm)
    # add PE to P edges

    add_vrf_loopbacks(g_vrf)
    # allocate route-targets per AS
    # This could later look at connected components for each ASN
    route_targets = {}
    for asn, devices in ank_utils.groupby("asn", g_vrf.nodes(vrf_role="PE")):
        asn_vrfs = [d.node_vrf_names for d in devices]
        # flatten list to unique set
        asn_vrfs = set(itertools.chain.from_iterable(asn_vrfs))
        route_targets[asn] = {vrf: "%s:%s" % (asn, index)
                              for index, vrf in enumerate(sorted(asn_vrfs), 1)}

    g_vrf.data.route_targets = route_targets

    for node in g_vrf:
        vrf_loopbacks = node.interfaces("is_loopback", "vrf_name")
        for index, interface in enumerate(vrf_loopbacks, start=101):
            interface.index = index

    for edge in g_vrf.edges():
        # Set the vrf of the edge to be that of the CE device (either src or
        # dst)
        edge.vrf = edge.src.vrf if edge.src.vrf_role is "CE" else edge.dst.vrf

    # map attributes to interfaces
    for edge in g_vrf.edges():
        for interface in edge.interfaces():
            interface.vrf_name = edge.vrf
