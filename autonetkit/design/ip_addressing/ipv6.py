import autonetkit.ank as ank_utils
import autonetkit.config
import autonetkit.log as log
from autonetkit.ank import sn_preflen_to_network
from netaddr import IPAddress

SETTINGS = autonetkit.config.settings

#@call_log


def manual_ipv6_loopback_allocation(anm):
    """Applies manual IPv6 allocation"""

    import netaddr
    g_ipv6 = anm['ipv6']
    g_in = anm['input']

    for l3_device in g_ipv6.l3devices():
        try:
            l3_device.loopback = IPAddress(l3_device['input'].loopback_v6)
        except netaddr.AddrFormatError:
            log.debug("Unable to parse IP address %s on %s",
                l3_device['input'].loopback_v6, l3_device)

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)
    try:
        loopback_subnet = g_in.data.ipv6_loopback_subnet
        loopback_prefix = g_in.data.ipv6_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                                               loopback_prefix)
    except Exception, e:
        log.info("Unable to parse specified ipv4 loopback subnets %s/%s")
    else:
        mismatched_nodes = [n for n in g_ipv6.l3devices()
                            if n.loopback and
                            n.loopback not in loopback_block]
        if len(mismatched_nodes):
            log.warning("IPv6 loopbacks set on nodes %s are not in global "
                        "loopback allocation block %s"
                        % (sorted(mismatched_nodes), loopback_block))

    loopback_blocks = {}
    for (asn, devices) in g_ipv6.groupby('asn').items():
        routers = [d for d in devices if d.is_router()]
        loopbacks = [r.loopback for r in routers]
        loopback_blocks[asn] = netaddr.cidr_merge(loopbacks)

    g_ipv6.data.loopback_blocks = loopback_blocks
    # formatted = {key: [str(v) for v in val] for key, val in loopback_blocks.items()}
    # log.info("Found loopback IP blocks %s", formatted)

#@call_log


def extract_ipv6_blocks(anm):

    # TODO: set all these blocks globally in config file, rather than repeated
    # in load, build_network, compile, etc

    from autonetkit.ank import sn_preflen_to_network
    from netaddr import IPNetwork
    g_in = anm['input']

    ipv6_defaults = SETTINGS["IP Addressing"]["v6"]

    try:
        infra_subnet = g_in.data.ipv6_infra_subnet
        infra_prefix = g_in.data.ipv6_infra_prefix
        infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, error:
        infra_block = IPNetwork(
            '%s/%s' % (ipv6_defaults["infra_subnet"],
                       ipv6_defaults["infra_prefix"]))
        if infra_subnet is None or infra_prefix is None:
            log.debug('Using default IPv6 infra_subnet %s', infra_block)
        else:
            log.warning('Unable to obtain IPv6 infra_subnet from input graph: %s, using default %s' % (
                error, infra_block))

    try:
        loopback_subnet = g_in.data.ipv6_loopback_subnet
        loopback_prefix = g_in.data.ipv6_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                                               loopback_prefix)
    except Exception, error:
        loopback_block = IPNetwork(
            '%s/%s' % (ipv6_defaults["loopback_subnet"],
                       ipv6_defaults["loopback_prefix"]))
        if loopback_subnet is None or loopback_prefix is None:
            log.debug('Using default IPv6 loopback_subnet %s',
                      loopback_block)
        else:
            log.warning('Unable to obtain IPv6 loopback_subnet from" input graph: %s, using default %s' % (
                error, loopback_block))

    try:
        vrf_loopback_subnet = g_in.data.ipv6_vrf_loopback_subnet
        vrf_loopback_prefix = g_in.data.ipv6_vrf_loopback_prefix
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet,
                                                   vrf_loopback_prefix)
    except Exception, e:
        vrf_loopback_block = IPNetwork(
            '%s/%s' % (ipv6_defaults["vrf_loopback_subnet"], ipv6_defaults["vrf_loopback_prefix"]))
        if vrf_loopback_subnet is None or vrf_loopback_prefix is None:
            log.debug('Using default IPv6 vrf_loopback_subnet %s' %
                      vrf_loopback_block)
        else:
            log.warning('Unable to obtain IPv6 vrf_loopback_subnet from input graph: %s, using default %s' % (
                e, vrf_loopback_block))

    return (infra_block, loopback_block, vrf_loopback_block)

#@call_log


def manual_ipv6_infrastructure_allocation(anm):
    """Applies manual IPv6 allocation"""

    import netaddr
    g_ipv6 = anm['ipv6']
    g_in = anm['input']
    log.info('Using specified IPv6 infrastructure allocation')

    for node in g_ipv6.l3devices():
        for interface in node.physical_interfaces():
            if not interface['input'].is_bound:
                continue  # unbound interface
            if not interface['ipv6'].is_bound:
                continue
            ip_address = netaddr.IPAddress(interface['input'
                                                     ].ipv6_address)
            prefixlen = interface['input'].ipv6_prefixlen
            interface.ip_address = ip_address
            interface.prefixlen = prefixlen
            cidr_string = '%s/%s' % (ip_address, prefixlen)
            interface.subnet = netaddr.IPNetwork(cidr_string)

    broadcast_domains = [d for d in g_ipv6 if d.broadcast_domain]

    # TODO: allow this to work with specified ip_address/subnet as well as
    # ip_address/prefixlen

    global_infra_block = None
    try:
        # Note this is only pickling up if explictly set in g_in
        infra_subnet = g_in.data.ipv6_infra_subnet
        infra_prefix = g_in.data.ipv6_infra_prefix
        global_infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        log.info("Unable to parse specified ipv4 infra subnets %s/%s")

    from netaddr import IPNetwork
    mismatched_interfaces = []

    for coll_dom in broadcast_domains:
        connected_interfaces = [edge.dst_int for edge in
                                coll_dom.edges()]
        cd_subnets = [IPNetwork('%s/%s' % (i.subnet.network,
                                           i.prefixlen)) for i in connected_interfaces]

        if global_infra_block is not None:
            mismatched_interfaces += [i for i in connected_interfaces
            if i.ip_address not in global_infra_block]

        if len(cd_subnets) == 0:
            log.warning("Collision domain %s is not connected to any nodes",
                        coll_dom)
            continue

        try:
            assert len(set(cd_subnets)) == 1
        except AssertionError:
            mismatch_subnets = '; '.join('%s: %s/%s' % (i,
                                                        i.subnet.network, i.prefixlen) for i in
                                         connected_interfaces)
            log.warning('Non matching subnets from collision domain %s: %s',
                        coll_dom, mismatch_subnets)
        else:
            coll_dom.subnet = cd_subnets[0]  # take first entry

        # apply to remote interfaces

        for edge in coll_dom.edges():
            edge.dst_int.subnet = coll_dom.subnet

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)
    # import autonetkit
    # autonetkit.update_vis(anm)
    if len(mismatched_interfaces):
        log.warning("IPv6 Infrastructure IPs %s are not in global "
                    "loopback allocation block %s"
                    % (sorted(mismatched_interfaces), global_infra_block))

    infra_blocks = {}
    for (asn, devices) in g_ipv6.groupby('asn').items():
        broadcast_domains = [d for d in devices if d.broadcast_domain]
        subnets = [cd.subnet for cd in broadcast_domains
                   if cd.subnet is not None]  # only if subnet is set
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    g_ipv6.data.infra_blocks = infra_blocks
    # formatted = {key: [str(v) for v in val] for key, val in infra_blocks.items()}
    # log.info("Found loopback IP blocks %s", formatted)


#@call_log


def build_ipv6(anm):
    """Builds IPv6 graph, using nodes and edges from IP graph"""
    import netaddr
    import autonetkit.plugins.ipv6 as ipv6

    # uses the nodes and edges from ipv4

    # TODO: do we also need to copy across the asn for broadcast domains?

    g_ipv6 = anm.add_overlay('ipv6')
    g_ip = anm['ip']
    g_in = anm['input']
    # retain if collision domain or not
    g_ipv6.add_nodes_from(g_ip, retain=['label', 'asn', 'allocate',
                                        'broadcast_domain'])
    g_ipv6.add_edges_from(g_ip.edges())

    # TODO: tidy up naming consitency of secondary_loopback_block and
    # vrf_loopback_block
    (infra_block, loopback_block, secondary_loopback_block) = \
        extract_ipv6_blocks(anm)

    if any(i for n in g_ip.nodes() for i in
           n.loopback_interfaces() if not i.is_loopback_zero):
        block_message = "IPv6 Secondary Loopbacks: %s" % secondary_loopback_block
        log.info(block_message)

    # TODO: replace this with direct allocation to interfaces in ip alloc
    # plugin
    allocated = sorted([n for n in g_ip if n['input'].loopback_v6])
    if len(allocated) == len(g_ip.l3devices()):
        # all allocated
        # TODO: need to infer subnetomanual_ipv6_loopback_allocation
        log.info("Using user-specified IPv6 loopback addresses")
        manual_ipv6_loopback_allocation(anm)
    else:
        log.info("Allocating from IPv6 loopback block: %s" % loopback_block)
        if len(allocated):
            log.warning(
                "Using automatic IPv6 loopback allocation. IPv6 loopback addresses specified on nodes %s will be ignored." % allocated)
        else:
            log.info("Automatically assigning IPv6 loopback addresses")

        ipv6.allocate_loopbacks(g_ipv6, loopback_block)

    l3_devices = [d for d in g_in if d.device_type in ('router', 'server')]

    manual_alloc_devices = set()
    for device in l3_devices:
        physical_interfaces = list(device.physical_interfaces())
        allocated = list(
            interface.ipv6_address for interface in physical_interfaces
            if interface.is_bound and interface['ipv6'].is_bound
            and interface['ip'].allocate is not False)

        #TODO: check for repeated code

#TODO: copy allocate from g_ip to g_ipv6
        if all(interface.ipv6_address for interface in
               physical_interfaces if interface.is_bound
               and interface['ipv6'].is_bound
               and interface['ip'].allocate is not False):
            # add as a manual allocated device
            manual_alloc_devices.add(device)

    if manual_alloc_devices == set(l3_devices):
        log.info("Using user-specified IPv6 infrastructure addresses")
        manual_alloc_ipv6_infrastructure = True
    else:
        log.info("Allocating from IPv6 Infrastructure block: %s" % infra_block)
        manual_alloc_ipv6_infrastructure = False
        # warn if any set
        allocated = []
        unallocated = []
        for node in l3_devices:
            allocated += sorted([i for i in node.physical_interfaces()
                                 if i.is_bound and i.ipv6_address])
            unallocated += sorted([i for i in node.physical_interfaces()
                                   if i.is_bound and not i.ipv6_address
                                   and i['ipv6'].is_bound])

        # TODO: what if IP is set but not a prefix?
        if len(allocated):
            # TODO: if set is > 50% of nodes then list those that are NOT set
            log.warning(
                "Using automatic IPv6 interface allocation. IPv6 interface addresses specified on interfaces %s will be ignored." % allocated)
        else:
            log.info("Automatically assigning IPv6 infrastructure addresses")

    if manual_alloc_ipv6_infrastructure:
        manual_ipv6_infrastructure_allocation(anm)
    else:
        ipv6.allocate_infra(g_ipv6, infra_block)
        # TODO: see if this is still needed or if can allocate direct from the
        # ipv6 allocation plugin
        for node in g_ipv6.l3devices():
            for interface in node:
                edges = list(interface.edges())
                if len(edges):
                    edge = edges[0]  # first (only) edge
                    # TODO: make this consistent
                    interface.ip_address = edge.ip
                    interface.subnet = edge.dst.subnet  # from collision domain

    ipv6.allocate_secondary_loopbacks(g_ipv6, secondary_loopback_block)
    for node in g_ipv6:
        node.static_routes = []

    for node in g_ipv6.routers():
        # TODO: test this code
        node.loopback_zero.ip_address = node.loopback
        node.loopback_zero.subnet = netaddr.IPNetwork("%s/32" % node.loopback)
        for interface in node.loopback_interfaces():
            if not interface.is_loopback_zero:
                # TODO: fix this inconsistency elsewhere
                interface.ip_address = interface.loopback

#@call_log
