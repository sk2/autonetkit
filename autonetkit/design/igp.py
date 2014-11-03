import autonetkit.log as log
import autonetkit.ank as ank_utils

from autonetkit.ank_utils import call_log

# TODO: extract the repeated code and use the layer2  and layer3 graphs


def build_igp(anm):
    build_ospf(anm)
    build_eigrp(anm)
    build_isis(anm)

    # Build a protocol summary graph
    g_igp = anm.add_overlay("igp")
    igp_protocols = ["ospf", "eigrp", "isis"]
    for protocol in igp_protocols:
        g_protocol = anm[protocol]
        g_igp.add_nodes_from(g_protocol, igp=protocol)
        g_igp.add_edges_from(g_protocol.edges(), igp=protocol)

#@call_log


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
    g_l3 = anm['layer3']
    g_phy = anm['phy']
    # add regardless, so allows quick check of node in anm['ospf'] in compilers
    g_ospf = anm.add_overlay("ospf")
    if not anm['phy'].data.enable_routing:
        g_ospf.log.info("Routing disabled, not configuring OSPF")
        return

    if not any(n.igp == "ospf" for n in g_phy):
        g_ospf.log.debug("No OSPF nodes")
        return

    ospf_nodes = [n for n in g_l3 if n['phy'].igp == "ospf"]
    g_ospf.add_nodes_from(ospf_nodes)
    g_ospf.add_edges_from(g_l3.edges(), warn=False)
    ank_utils.copy_int_attr_from(g_l3, g_ospf, "multipoint")

    # TODO: work out why this doesnt work
    #ank_utils.copy_int_attr_from(g_in, g_ospf, "ospf_cost", dst_attr="cost",  type=int, default = 1)
    for node in g_ospf:
        for interface in node.physical_interfaces():
            interface.cost = 1

    ank_utils.copy_attr_from(g_in, g_ospf, "ospf_area", dst_attr="area")
    #ank_utils.copy_edge_attr_from(g_in, g_ospf, "ospf_cost", dst_attr="cost",  type=int, default = 1)
    ank_utils.copy_attr_from(
        g_in, g_ospf, "custom_config_ospf", dst_attr="custom_config")

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
                    router.log.warning("Invalid OSPF area %s. Using default"
                                       " of %s" % (router.area, default_area))
                    router.area = default_area

    # TODO: use interfaces throughout, rather than edges
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
            elif router.area in area_zero_ids:
                router.log.debug(
                    "Router belongs to area %s but has no area zero interfaces",
                    router.area)
                router.type = "backbone ABR"
            else:
                router.log.warning(
                    "spans multiple areas but is not a member of area 0")
                router.type = "INVALID"

    if (any(area_zero_int in router.areas for router in g_ospf) and
            any(area_zero_ip in router.areas for router in g_ospf)):
        router.log.warning("Using both area 0 and area 0.0.0.0")

    for link in g_ospf.edges():
        if not link.cost:
            link.cost = 1

    # map areas and costs onto interfaces
    # TODO: later map them directly rather than with edges - part of
    # the transition
    for edge in g_ospf.edges():
        for interface in edge.interfaces():
            interface.cost = edge.cost
            interface.area = edge.area
            interface.multipoint = edge.multipoint

    for router in g_ospf:
        router.loopback_zero.area = router.area
        router.loopback_zero.cost = 0
        router.process_id = router.asn

#@call_log


def ip_to_net_ent_title_ios(ip_addr):
    """ Converts an IP address into an OSI Network Entity Title
    suitable for use in IS-IS on IOS.

    >>> from netaddr import IPAddress
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

#@call_log


def build_eigrp(anm):
    """Build eigrp overlay"""
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['isis'] in compilers
    g_l3 = anm['layer3']
    g_eigrp = anm.add_overlay("eigrp")
    g_phy = anm['phy']

    if not anm['phy'].data.enable_routing:
        g_eigrp.log.info("Routing disabled, not configuring EIGRP")
        return

    if not any(n.igp == "eigrp" for n in g_phy):
        log.debug("No EIGRP nodes")
        return
    eigrp_nodes = [n for n in g_l3 if n['phy'].igp == "eigrp"]
    g_eigrp.add_nodes_from(eigrp_nodes)
    g_eigrp.add_edges_from(g_l3.edges(), warn=False)
    ank_utils.copy_int_attr_from(g_l3, g_eigrp, "multipoint")

    ank_utils.copy_attr_from(
        g_in, g_eigrp, "custom_config_eigrp", dst_attr="custom_config")

# Merge and explode switches
    ank_utils.aggregate_nodes(g_eigrp, g_eigrp.switches())
    exploded_edges = ank_utils.explode_nodes(g_eigrp,
                                             g_eigrp.switches())
    for edge in exploded_edges:
        edge.multipoint = True

    g_eigrp.remove_edges_from(
        [link for link in g_eigrp.edges() if link.src.asn != link.dst.asn])

    for node in g_eigrp:
        node.process_id = node.asn

    for link in g_eigrp.edges():
        link.metric = 1  # default

    for edge in g_eigrp.edges():
        for interface in edge.interfaces():
            interface.metric = edge.metric
            interface.multipoint = edge.multipoint

#@call_log


def build_network_entity_title(anm):
    g_isis = anm['isis']
    g_ipv4 = anm['ipv4']
    for node in g_isis.routers():
        ip_node = g_ipv4.node(node)
        node.net = ip_to_net_ent_title_ios(ip_node.loopback)


def build_isis(anm):
    """Build isis overlay"""
    g_in = anm['input']
    # add regardless, so allows quick check of node in anm['isis'] in compilers
    g_l3 = anm['layer3']
    g_phy = anm['phy']
    g_isis = anm.add_overlay("isis")

    if not anm['phy'].data.enable_routing:
        g_isis.log.info("Routing disabled, not configuring ISIS")
        return

    if not any(n.igp == "isis" for n in g_phy):
        g_isis.log.debug("No ISIS nodes")
        return

    isis_nodes = [n for n in g_l3 if n['phy'].igp == "isis"]
    g_isis.add_nodes_from(isis_nodes)
    g_isis.add_edges_from(g_l3.edges(), warn=False)
    ank_utils.copy_int_attr_from(g_l3, g_isis, "multipoint")

    ank_utils.copy_attr_from(
        g_in, g_isis, "custom_config_isis", dst_attr="custom_config")

    g_isis.remove_edges_from(
        [link for link in g_isis.edges() if link.src.asn != link.dst.asn])

    build_network_entity_title(anm)

    for node in g_isis.routers():
        node.process_id = node.asn

    for link in g_isis.edges():
        link.metric = 1  # default

    for edge in g_isis.edges():
        for interface in edge.interfaces():
            interface.metric = edge.metric
            interface.multipoint = edge.multipoint
