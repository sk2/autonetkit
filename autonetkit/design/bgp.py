import autonetkit.log as log
import autonetkit.ank as ank_utils

def three_tier_ibgp_corner_cases(rtrs):
    """Calculate edges for iBGP l3 clusters that don't contain a HRR.
    Connects l1 to l3 directly"""
    up_links = []
    down_links = []
    over_links = []
    for l3_cluster, l3d in ank_utils.groupby("ibgp_l3_cluster", rtrs):
        l3d = list(l3d)
        for l2_cluster, l2d in ank_utils.groupby("ibgp_l2_cluster", l3d):
            l2d = list(l2d)
            if any(r.ibgp_level == 2 for r in l2d):
                log.debug("Cluster (%s, %s) has l2 devices, not "
                          "adding extra links" % (l3_cluster, l2_cluster))
            elif all(r.ibgp_level == 1 for r in l2d):
                # No l2 or l3 routers -> full-mesh of l1 routers
                # test if l3_cluster contains any l3 routers
                if any(r.ibgp_level == 3 for r in l3d):
                    l1_rtrs = [r for r in l2d if r.ibgp_level == 1]
                    l3_rtrs = [r for r in l3d if r.ibgp_level == 3]
                    if not(len(l1_rtrs) and len(l3_rtrs)):
                        log.debug("Cluster (%s, %s) has no level 2 iBGP routers."
                          "Connecting l1 routers (%s) to l3 routers (%s)"
                          % (l3_cluster, l2_cluster, l1_rtrs, l3_rtrs))
                        break  # no routers to connect

                    l1_l3_up_links = [(s, t) for s in l1_rtrs for t in l3_rtrs]
                    up_links += l1_l3_up_links
                    down_links += [(t, s) for (s, t) in l1_l3_up_links]
                else:
                    over_links += [(s, t) for s in l2d for t in l2d if s != t]
                    log.debug("Cluster (%s, %s) has no level 2 or 3 "
                        "iBGP routers. Connecting l1 routers (%s) in full-mesh"
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

    l1_l3_up_links, l1_l3_down_links, l1_l3_over_links = three_tier_ibgp_corner_cases(routers)
    up_links += l1_l3_up_links
    down_links += l1_l3_down_links
    over_links += l1_l3_over_links

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
            if e.src in ebgp_switches or e.dst in ebgp_switches),
    bidirectional=True, type='ebgp')
    ank_utils.aggregate_nodes(g_ebgp, ebgp_switches, retain="edge_id")
    # need to recalculate as may have aggregated
    ebgp_switches = list(g_ebgp.nodes("is_switch"))
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
            #TODO: check when this is reached - as RR is not HRR.... due to naming/levels mapping
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