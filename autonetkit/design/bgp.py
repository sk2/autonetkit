import autonetkit.ank as ank_utils
import autonetkit.log as log


from autonetkit.ank_utils import call_log

@call_log
def build_ibgp_v4(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    #TODO: base on generic ibgp graph, rather than bgp graph
    g_bgp = anm['bgp']
    g_phy = anm['phy']
    g_ibgpv4 = anm.add_overlay("ibgp_v4", directed=True)
    ipv4_nodes = set(g_phy.nodes("is_router", "use_ipv4"))
    g_ibgpv4.add_nodes_from((n for n in g_bgp if n in ipv4_nodes),
            retain = ["ibgp_level", "ibgp_role", "hrr_cluster", "rr_cluster"] )
    g_ibgpv4.add_edges_from(g_bgp.edges(type="ibgp"), retain="direction")

@call_log
def build_ibgp_v6(anm):
    #TODO: remove the bgp layer and have just ibgp and ebgp
    # TODO: build from design rules, currently just builds from ibgp links in bgp layer
    #TODO: base on generic ibgp graph, rather than bgp graph
    g_bgp = anm['bgp']
    g_phy = anm['phy']
    g_ibgpv6 = anm.add_overlay("ibgp_v6", directed=True)
    ipv6_nodes = set(g_phy.nodes("is_router", "use_ipv6"))
    g_ibgpv6.add_nodes_from((n for n in g_bgp if n in ipv6_nodes),
            retain = ["ibgp_level", "ibgp_role", "hrr_cluster", "rr_cluster"] )
    g_ibgpv6.add_edges_from(g_bgp.edges(type="ibgp"), retain="direction")

@call_log
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


@call_log
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
    g_ebgp.log.debug("eBGP switches are %s" % ebgp_switches)
    g_ebgp.add_edges_from((e for e in g_in.edges()
            if e.src in ebgp_switches or e.dst in ebgp_switches),
    bidirectional=True, type='ebgp')
    ank_utils.aggregate_nodes(g_ebgp, ebgp_switches)
    # need to recalculate as may have aggregated
    ebgp_switches = list(g_ebgp.nodes("is_switch"))
    g_ebgp.log.debug("aggregated eBGP switches are %s" % ebgp_switches)
    exploded_edges = ank_utils.explode_nodes(g_ebgp, ebgp_switches)
    same_asn_edges = []
    for edge in exploded_edges:
        if edge.src.asn == edge.dst.asn:
            same_asn_edges.append(edge)
        else:
            edge.multipoint = True
    """TODO: remove up to here once compiler updated"""

    g_ebgp.remove_edges_from(same_asn_edges)


@call_log
def build_ibgp(anm):
    g_in = anm['input']
    g_phy = anm['phy']
    g_bgp = anm['bgp']


    #TODO: build direct to ibgp graph - can construct combined bgp for vis

    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_level")
    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_l2_cluster", "hrr_cluster", default = None)
    ank_utils.copy_attr_from(g_in, g_bgp, "ibgp_l3_cluster", "rr_cluster", default = None)

    ank_utils.set_node_default(g_bgp,  is_hrr = None, is_rr = None, is_rrc=None)


    """Levels:
    0: no BGP
    1: RRC
    2: HRR
    3: RR
    """

    #TODO: add more detailed logging

    for n in g_bgp:
        # Tag with label to make logic clearer
        if n.ibgp_level is None:
            # No level set -> treat as RRC
            if (n.rr_cluster is None) and (n.hrr_cluster is None):
                n.top_level_peer = True
            else:
                n.ibgp_level = 1

            #TODO: if top-level, then don't mark as RRC

        if n.ibgp_level == 0:
            n.is_no_ibgp = True
        elif n.ibgp_level == 1:
            n.is_rrc = True
        elif n.ibgp_level == 2:
            n.is_hrr = True
        elif n.ibgp_level == 3:
            n.is_rr = True

    ibgp_nodes = [n for n in g_bgp if not n.ibgp_level == 0]


    # Notify user of non-ibgp nodes
    non_ibgp_nodes = [n for n in g_bgp if n.ibgp_level == 0]
    if len(non_ibgp_nodes) < 10:
        log.info("Skipping iBGP for iBGP disabled nodes: %s" % non_ibgp_nodes)
    elif len(non_ibgp_nodes) >= 10:
        log.info("Skipping iBGP for iBGP disabled nodes: refer to visualization for resulting topology.")

    for asn, asn_devices in ank_utils.groupby("asn", ibgp_nodes):
        asn_devices = list(asn_devices)

        asn_rrs = [n for n in asn_devices if n.is_rr]
        over_links = [(s, t) for s in asn_rrs for t in asn_rrs if s != t]
        g_bgp.add_edges_from(over_links, type='ibgp', direction='over')

        top_level_peers = [n for n in asn_devices if n.top_level_peer]
        # Full mesh top level peers
        over_links = [(s, t) for s in top_level_peers for t in top_level_peers if s != t]
        g_bgp.add_edges_from(over_links, type='ibgp', direction='over')
        # Mesh with ASN rrs
        over_links = [(s, t) for s in top_level_peers for t in asn_rrs if s != t]
        g_bgp.add_edges_from(over_links, type='ibgp', direction='over')
        # and other direction
        over_links = [(s, t) for s in asn_rrs for t in top_level_peers if s != t]
        g_bgp.add_edges_from(over_links, type='ibgp', direction='over')

        for rr_cluster, rr_cluster_rtrs in ank_utils.groupby("rr_cluster", asn_devices):
            rr_cluster_rtrs = list(rr_cluster_rtrs)

            rr_cluster_rrs = [n for n in rr_cluster_rtrs if n.is_rr]
            rr_cluster_hrrs = [n for n in rr_cluster_rtrs if n.is_hrr]

            rr_parents = rr_cluster_rrs # Default is to parent HRRs to RRs in same rr_cluster
            if len(rr_cluster_hrrs) and not len(rr_cluster_rrs):
                if rr_cluster is None:
                    # Special case: connect to global RRs
                    rr_parents = asn_rrs
                else:
                    log.warning("RR Cluster %s in ASN%s has no RRs" % (rr_cluster, asn))

            # Connect HRRs to RRs in the same rr_cluster
            up_links = [(s, t) for s in rr_cluster_hrrs for t in rr_parents]
            g_bgp.add_edges_from(up_links, type='ibgp', direction='over')
            down_links = [(t, s) for (s, t) in up_links]
            g_bgp.add_edges_from(down_links, type='ibgp', direction='over')

            for hrr_cluster, hrr_cluster_rtrs in ank_utils.groupby("hrr_cluster", rr_cluster_rtrs):
                hrr_cluster_rtrs = list(hrr_cluster_rtrs)

                hrr_cluster_hrrs = [n for n in hrr_cluster_rtrs if n.is_hrr]
                hrr_cluster_rrcs = [n for n in hrr_cluster_rtrs if n.is_rrc]

                # Connect RRCs
                if len(hrr_cluster_hrrs):
                    # hrr_cluster_hrrs in this hrr_cluster -> connect RRCs to these
                    up_links = [(s, t) for s in hrr_cluster_rrcs for t in hrr_cluster_hrrs]
                    g_bgp.add_edges_from(up_links, type='ibgp', direction='up')
                    down_links = [(t, s) for (s, t) in up_links]
                    g_bgp.add_edges_from(down_links, type='ibgp', direction='down')
                elif len(rr_cluster_rrs):
                    # No HRRs in this cluster, connect RRCs to RRs in the same RR cluster
                    #TODO: warn here: might not be what the user wanted
                    up_links = [(s, t) for s in hrr_cluster_rrcs for t in rr_cluster_rrs]
                    g_bgp.add_edges_from(up_links, type='ibgp', direction='up')
                    down_links = [(t, s) for (s, t) in up_links]
                    g_bgp.add_edges_from(down_links, type='ibgp', direction='down')
                else:
                    # Full-mesh
                    over_links = [(s, t) for s in hrr_cluster_rrcs for t in hrr_cluster_rrcs if s!=t]
                    g_bgp.add_edges_from(over_links, type='ibgp', direction='over')
                    if (rr_cluster is None) and (hrr_cluster is None):
                        # Connect to RRs at ASN level
                        log.debug("RRCs %s in global group, connecting to global RRs" % hrr_cluster_rrcs)
                        up_links = [(s, t) for s in hrr_cluster_rrcs for t in asn_rrs]
                        g_bgp.add_edges_from(up_links, type='ibgp', direction='up')
                        down_links = [(t, s) for (s, t) in up_links]
                        g_bgp.add_edges_from(down_links, type='ibgp', direction='down')

                    #TODO: Special case: if no hrr or rr cluster set, then connect to global RRs

        #TODO: add consistency check to ensure is_hrr etc matches
    """Levels:
    0: no BGP
    1: RRC
    2: HRR
    3: RR
    """
    levels_to_roles = {
    0: "Disabled",
    1: "RR Client",
    2: "Hierarchical RR",
    3: "Route Reflector",
    }

    expected_level_values = {
    0: (True, None, None, None),
    1: (None, True, None, None),
    2: (None, None, True, None),
    3: (None, None, None, True),
    }

    for node in g_bgp:
        #TODO: move this to the validate stage
        if node.top_level_peer:
            continue # don't check the roles
        values = (node.is_no_ibgp, node.is_rrc, node.is_hrr, node.is_rr)
        if values.count(True) != 1:
            log.warning("Inconsistency in iBGP attributes")
        else:
            if values != expected_level_values[node.ibgp_level]:
                log.warning("Inconsistency in iBGP attributes")


    for node in g_bgp:
        if node.top_level_peer:
            node.ibgp_role = "Top-level Peer"
        else:
            node.ibgp_role = levels_to_roles[node.ibgp_level]


@call_log
def build_bgp(anm):
    """Build iBGP end eBGP overlays"""
    # eBGP
    g_in = anm['input']
    g_phy = anm['phy']

    if not anm['phy'].data.enable_routing:
        log.info("Routing disabled, not configuring BGP")
        return

    build_ebgp(anm)
    build_ebgp_v4(anm)
    build_ebgp_v6(anm)

    """TODO: remove from here once compiler updated"""
    g_bgp = anm.add_overlay("bgp", directed=True)
    g_bgp.add_nodes_from(g_in.nodes("is_router"))
    ebgp_edges = [edge for edge in g_in.edges() if not edge.attr_equal("asn")]
    g_bgp.add_edges_from(ebgp_edges, bidirectional=True, type='ebgp')

    ebgp_switches = [n for n in g_in.nodes("is_switch")
            if not ank_utils.neigh_equal(g_phy, n, "asn")]
    g_bgp.add_nodes_from(ebgp_switches, retain=['asn'])
    log.debug("eBGP switches are %s" % ebgp_switches)
    g_bgp.add_edges_from((e for e in g_in.edges()
            if e.src in ebgp_switches or e.dst in ebgp_switches), bidirectional=True, type='ebgp')
    ank_utils.aggregate_nodes(g_bgp, ebgp_switches)
    ebgp_switches = list(g_bgp.nodes("is_switch")) # need to recalculate as may have aggregated
    log.debug("aggregated eBGP switches are %s" % ebgp_switches)
    exploded_edges = ank_utils.explode_nodes(g_bgp, ebgp_switches)

    same_asn_edges = []
    for edge in exploded_edges:
        if edge.src.asn == edge.dst.asn:
            same_asn_edges.append(edge)
        else:
            edge.multipoint = True
    """TODO: remove up to here once compiler updated"""

    g_bgp.remove_edges_from(same_asn_edges)


    build_ibgp(anm)

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
