import autonetkit.log as log
import autonetkit.ank as ank_utils

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

    """
    import netaddr
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['ospf'] in compilers
    g_ospf = anm.add_overlay("ospf")

    if not anm['phy'].data.enable_routing:
        log.info("Routing disabled, not configuring OSPF")
        return

    if not any(n.igp == "ospf" for n in g_in):
        log.debug("No OSPF nodes")
        return

    g_ospf.add_nodes_from(g_in.nodes("is_router", igp = "ospf"), retain=['asn'])
    g_ospf.add_nodes_from(g_in.nodes("is_server", igp = "ospf"), retain=['asn'])
    g_ospf.add_nodes_from(g_in.nodes("is_switch"), retain=['asn'])
    g_ospf.add_edges_from(g_in.edges(), retain=['edge_id'])

    ank_utils.copy_attr_from(g_in, g_ospf, "ospf_area", dst_attr="area")
    ank_utils.copy_edge_attr_from(g_in, g_ospf, "ospf_cost",
        dst_attr="cost",  type=float)

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

    #TODO: use interfaces throughout, rather than edges
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

def build_eigrp(anm):
    """Build eigrp overlay"""
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['isis'] in compilers
    g_eigrp = anm.add_overlay("eigrp")

    if not anm['phy'].data.enable_routing:
        log.info("Routing disabled, not configuring EIGRP")
        return

    if not any(n.igp == "eigrp" for n in g_in):
        log.debug("No EIGRP nodes")
        return
    g_ipv4 = anm['ipv4']
    g_eigrp.add_nodes_from(g_in.nodes("is_router",
        igp = "eigrp"), retain=['asn'])
    g_eigrp.add_nodes_from(g_in.nodes("is_server",
        igp = "eigrp"), retain=['asn'])
    g_eigrp.add_nodes_from(g_in.nodes("is_switch"), retain=['asn'])
    g_eigrp.add_edges_from(g_in.edges(), retain=['edge_id'])
# Merge and explode switches
    ank_utils.aggregate_nodes(g_eigrp, g_eigrp.nodes("is_switch"),
                              retain="edge_id")
    exploded_edges = ank_utils.explode_nodes(g_eigrp,
        g_eigrp.nodes("is_switch"),
                            retain="edge_id")
    for edge in exploded_edges:
        edge.multipoint = True

    g_eigrp.remove_edges_from(
        [link for link in g_eigrp.edges() if link.src.asn != link.dst.asn])

    for node in g_eigrp:
        ip_node = g_ipv4.node(node)
        node.net = ip_to_net_ent_title_ios(ip_node.loopback)
        node.name = "one"  # default

    for link in g_eigrp.edges():
        link.metric = 1  # default

    for edge in g_eigrp.edges():
        for interface in edge.interfaces():
            interface.metric = edge.metric
            interface.multipoint = edge.multipoint

def build_isis(anm):
    """Build isis overlay"""
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['isis'] in compilers
    g_isis = anm.add_overlay("isis")

    if not anm['phy'].data.enable_routing:
        log.info("Routing disabled, not configuring EIGRP")
        return

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

    for node in g_isis.nodes("is_router"):
        ip_node = g_ipv4.node(node)
        node.net = ip_to_net_ent_title_ios(ip_node.loopback)
        node.process_id = 1  # default

    for link in g_isis.edges():
        link.metric = 1  # default

    for edge in g_isis.edges():
        for interface in edge.interfaces():
            interface.metric = edge.metric
            interface.multipoint = edge.multipoint
