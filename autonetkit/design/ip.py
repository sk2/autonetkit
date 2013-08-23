import autonetkit.log as log
import autonetkit.ank as ank_utils

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
    g_ipv4 = anm['ipv4']

    for node in g_ipv4.nodes("is_l3device"):
        for interface in node.physical_interfaces:
            if not interface['input'].is_bound:
                continue # unbound interface
            ip_address = netaddr.IPAddress(interface['input'].ipv4_address)
            prefixlen = interface['input'].ipv4_prefixlen
            interface.ip_address = ip_address
            interface.prefixlen = prefixlen
            cidr_string = "%s/%s" % (ip_address, prefixlen)
            interface.subnet = netaddr.IPNetwork(cidr_string)

    collision_domains = [d for d in g_ipv4 if d.collision_domain]
    #TODO: allow this to work with specified ip_address/subnet as well as ip_address/prefixlen
    from netaddr import IPNetwork
    for coll_dom in collision_domains:
        connected_interfaces = [edge.dst_int for edge in coll_dom.edges()]
        cd_subnets = [IPNetwork("%s/%s" % (i.subnet.network, i.prefixlen))
            for i in connected_interfaces]

        try:
            assert(len(set(cd_subnets)) == 1)
        except AssertionError:
            log.warning("Non matching subnets from collision domain %s" % coll_dom)
        else:
            coll_dom.subnet = cd_subnets[0] # take first entry

        # apply to remote interfaces
        for edge in coll_dom.edges():
            edge.dst_int.subnet = coll_dom.subnet

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)
    #import autonetkit
    #autonetkit.update_http(anm)
    infra_blocks = {}
    for asn, devices in g_ipv4.groupby("asn").items():
        collision_domains = [d for d in devices if d.collision_domain]
        subnets = [cd.subnet for cd in collision_domains]
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    g_ipv4.data.infra_blocks = infra_blocks

def manual_ipv4_loopback_allocation(anm):
    """Applies manual IPv4 allocation"""
    import netaddr
    g_ipv4 = anm['ipv4']

    for l3_device in g_ipv4.nodes("is_l3device"):
        l3_device.loopback = l3_device['input'].loopback_v4

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
        ank_utils.split(g_ip, edges_to_split,
            retain=['edge_id', 'split'], id_prepend = "cd"))
    for node in split_created_nodes:
        node['graphics'].x = ank_utils.neigh_average(g_ip, node, "x",
           g_graphics) + 0.1
         # temporary fix for gh-90
        node['graphics'].y = ank_utils.neigh_average(g_ip, node, "y",
             g_graphics) + 0.1
            # temporary fix for gh-90
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
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet,
            vrf_loopback_prefix)
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
    ank_utils.copy_attr_from(g_ip, g_ipv4, "asn",
        nbunch = g_ipv4.nodes("collision_domain"))
    g_ipv4.add_edges_from(g_ip.edges())

    # check if ip ranges have been specified on g_in
    infra_block, loopback_block, vrf_loopback_block = extract_ipv4_blocks(anm)

    # See if IP addresses specified on each interface
    l3_devices = [d for d in g_in if d.device_type in ("router", "server")]

    manual_alloc_devices = set()
    for device in l3_devices:
        physical_interfaces = list(device.physical_interfaces)
        if all(interface.ipv4_address for interface in physical_interfaces
            if interface.is_bound ):
            manual_alloc_devices.add(device) # add as a manual allocated device

    if manual_alloc_devices == set(l3_devices):
        manual_alloc_ipv4_infrastructure = True
    else:
        manual_alloc_ipv4_infrastructure = False

    #TODO: need to set allocate_ipv4 by default in the readers
    if manual_alloc_ipv4_infrastructure:
        manual_ipv4_infrastructure_allocation(anm)
    else:
        ipv4.allocate_infra(g_ipv4, infra_block)

    if g_in.data.alloc_ipv4_loopbacks is False:
        manual_ipv4_loopback_allocation(anm)
    else:
        ipv4.allocate_loopbacks(g_ipv4, loopback_block)

    #TODO: need to also support secondary_loopbacks for IPv6
    #TODO: only call if secondaries are set
    ipv4.allocate_vrf_loopbacks(g_ipv4, vrf_loopback_block)

    #TODO: replace this with direct allocation to interfaces in ip alloc plugin
    for node in g_ipv4.nodes("is_l3device"):
        node.loopback_zero.ip_address = node.loopback