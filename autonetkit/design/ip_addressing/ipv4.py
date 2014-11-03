import autonetkit.ank as ank_utils
import autonetkit.config
import autonetkit.log as log
from netaddr import IPAddress
from autonetkit.ank import sn_preflen_to_network

SETTINGS = autonetkit.config.settings


# TODO: add unit tests for each function here and in ipv6

def extract_ipv4_blocks(anm):

    # TODO: set all these blocks globally in config file, rather than repeated
    # in load, build_network, compile, etc

    from netaddr import IPNetwork
    g_in = anm['input']
    ipv4_defaults = SETTINGS["IP Addressing"]["v4"]

    # TODO: wrap these in a common function

    try:
        infra_subnet = g_in.data.ipv4_infra_subnet
        infra_prefix = g_in.data.ipv4_infra_prefix
        infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        infra_block = IPNetwork(
            '%s/%s' % (ipv4_defaults["infra_subnet"], ipv4_defaults["infra_prefix"]))
        if infra_subnet is None or infra_prefix is None:
            log.debug('Using default IPv4 infra_subnet %s' % infra_block)
        else:
            log.warning('Unable to obtain IPv4 infra_subnet from input graph: %s, using default %s' % (
                e, infra_block))

    try:
        loopback_subnet = g_in.data.ipv4_loopback_subnet
        loopback_prefix = g_in.data.ipv4_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                                               loopback_prefix)
    except Exception, e:
        loopback_block = IPNetwork(
            '%s/%s' % (ipv4_defaults["loopback_subnet"], ipv4_defaults["loopback_prefix"]))
        if loopback_subnet is None or loopback_prefix is None:
            log.debug('Using default IPv4 loopback_subnet %s' % loopback_block)
        else:
            log.warning('Unable to obtain IPv4 loopback_subnet from input graph: %s, using default %s' % (
                e, loopback_block))

    try:
        vrf_loopback_subnet = g_in.data.ipv4_vrf_loopback_subnet
        vrf_loopback_prefix = g_in.data.ipv4_vrf_loopback_prefix
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet,
                                                   vrf_loopback_prefix)
    except Exception, e:
        vrf_loopback_block = IPNetwork(
            '%s/%s' % (ipv4_defaults["vrf_loopback_subnet"], ipv4_defaults["vrf_loopback_prefix"]))
        if vrf_loopback_subnet is None or vrf_loopback_prefix is None:
            log.debug('Using default IPv4 vrf_loopback_subnet %s' %
                      vrf_loopback_block)
        else:
            log.warning('Unable to obtain IPv4 vrf_loopback_subnet from input graph: %s, using default %s' % (
                e, vrf_loopback_block))

    return (infra_block, loopback_block, vrf_loopback_block)


def manual_ipv4_infrastructure_allocation(anm):
    """Applies manual IPv4 allocation"""

    import netaddr
    g_ipv4 = anm['ipv4']
    g_in = anm['input']
    log.info('Using specified IPv4 infrastructure allocation')

    for node in g_ipv4.l3devices():
        for interface in node.physical_interfaces():
            if not interface['input'].is_bound:
                continue  # unbound interface
            if not interface['ipv4'].is_bound:
                continue
            if interface['ip'].allocate is False:
                # TODO: copy interface allocate attribute across
                continue

            ip_address = netaddr.IPAddress(interface['input'
                                                     ].ipv4_address)
            prefixlen = interface['input'].ipv4_prefixlen
            interface.ip_address = ip_address
            interface.prefixlen = prefixlen
            cidr_string = '%s/%s' % (ip_address, prefixlen)
            interface.subnet = netaddr.IPNetwork(cidr_string)

    broadcast_domains = [d for d in g_ipv4 if d.broadcast_domain]

    # TODO: allow this to work with specified ip_address/subnet as well as
    # ip_address/prefixlen

    global_infra_block = None
    try:
        # Note this is only pickling up if explictly set in g_in
        infra_subnet = g_in.data.ipv4_infra_subnet
        infra_prefix = g_in.data.ipv4_infra_prefix
        global_infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        log.info("Unable to parse specified ipv4 infra subnets %s/%s")

    mismatched_interfaces = []
    from netaddr import IPNetwork
    for coll_dom in broadcast_domains:
        if coll_dom.allocate is False:
            continue

        # TODO: use neighbor_interfaces()
        connected_interfaces = [edge.dst_int for edge in
                                coll_dom.edges()]

        connected_interfaces = [i for i in connected_interfaces
                                if i.node.is_l3device()]

        cd_subnets = [IPNetwork('%s/%s' % (i.subnet.network,
                                           i.prefixlen)) for i in connected_interfaces
                      if i['ip'].allocate is not False]

        # mismatched_interfaces += [i for i in connected_interfaces
        # if i.
        if global_infra_block is not None:
            mismatched_interfaces += [i for i in connected_interfaces
                                      if i.ip_address not in global_infra_block]

        if len(cd_subnets) == 0:
            log.warning(
                "Collision domain %s is not connected to any nodes" % coll_dom)
            continue

        try:
            assert len(set(cd_subnets)) == 1
        except AssertionError:
            mismatch_subnets = '; '.join('%s: %s/%s' % (i,
                                                        i.subnet.network, i.prefixlen) for i in
                                         connected_interfaces)
            log.warning('Non matching subnets from collision domain %s: %s'
                        % (coll_dom, mismatch_subnets))
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
        log.warning("IPv4 Infrastructure IPs %s are not in global "
                    "loopback allocation block %s"
                    % (sorted(mismatched_interfaces), global_infra_block))

    infra_blocks = {}
    for (asn, devices) in g_ipv4.groupby('asn').items():
        broadcast_domains = [d for d in devices if d.broadcast_domain]
        subnets = [cd.subnet for cd in broadcast_domains
                   if cd.subnet is not None]  # only if subnet is set
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    # formatted = {key: [str(v) for v in val] for key, val in infra_blocks.items()}
    # log.info("Found infrastructure IP blocks %s", formatted)
    g_ipv4.data.infra_blocks = infra_blocks


#@call_log
def manual_ipv4_loopback_allocation(anm):
    """Applies manual IPv4 allocation"""

    import netaddr
    g_ipv4 = anm['ipv4']
    g_in = anm['input']

    for l3_device in g_ipv4.l3devices():
        try:
            l3_device.loopback = IPAddress(l3_device['input'].loopback_v4)
        except netaddr.AddrFormatError:
            log.debug("Unable to parse IP address %s on %s",
                      l3_device['input'].loopback_v6, l3_device)

    try:
        loopback_subnet = g_in.data.ipv4_loopback_subnet
        loopback_prefix = g_in.data.ipv4_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                                               loopback_prefix)
    except Exception, e:
        log.info("Unable to parse specified ipv4 loopback subnets %s/%s")
    else:
        mismatched_nodes = [n for n in g_ipv4.l3devices()
                            if n.loopback and n.loopback not in loopback_block]
        if len(mismatched_nodes):
            log.warning("IPv4 loopbacks set on nodes %s are not in global "
                        "loopback allocation block %s"
                        % (sorted(mismatched_nodes), loopback_block))

    # mismatch = [n for n in g_ipv4.l3devices() if n.loopback not in

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)

    loopback_blocks = {}
    for (asn, devices) in g_ipv4.groupby('asn').items():
        routers = [d for d in devices if d.is_router()]
        loopbacks = [r.loopback for r in routers]
        loopback_blocks[asn] = netaddr.cidr_merge(loopbacks)

    g_ipv4.data.loopback_blocks = loopback_blocks
    # formatted = {key: [str(v) for v in val] for key, val in loopback_blocks.items()}
    #log.info("Found loopback IP blocks %s", formatted)


#@call_log
def build_ipv4(anm, infrastructure=True):
    """Builds IPv4 graph"""

    import autonetkit.plugins.ipv4 as ipv4
    import netaddr
    g_ipv4 = anm.add_overlay('ipv4')
    g_ip = anm['ip']
    g_in = anm['input']
    # retain if collision domain or not
    g_ipv4.add_nodes_from(g_ip, retain=['label', 'allocate',
                                        'broadcast_domain'])

    # Copy ASN attribute chosen for collision domains (used in alloc algorithm)

    ank_utils.copy_attr_from(
        g_ip, g_ipv4, 'asn', nbunch=g_ipv4.nodes('broadcast_domain'))
    # work around until fall-through implemented
    vswitches = [n for n in g_ip.nodes()
                 if n['layer2'].device_type == "switch"
                 and n['layer2'].device_subtype == "virtual"]
    ank_utils.copy_attr_from(g_ip, g_ipv4, 'asn', nbunch=vswitches)
    g_ipv4.add_edges_from(g_ip.edges())

    # check if ip ranges have been specified on g_in

    (infra_block, loopback_block, vrf_loopback_block) = \
        extract_ipv4_blocks(anm)

# TODO: don't present if using manual allocation
    if any(i for n in g_ip.nodes() for i in
           n.loopback_interfaces() if not i.is_loopback_zero):
        block_message = "IPv4 Secondary Loopbacks: %s" % vrf_loopback_block
        log.info(block_message)

    # See if IP addresses specified on each interface

    # do we need this still? in ANM? - differnt because input graph.... but
    # can map back to  self overlay first then phy???
    l3_devices = [d for d in g_in if d.device_type in ('router', 'server')]

    # TODO: need to account for devices whose interfaces are in only e.g. vpns

    manual_alloc_devices = set()
    for device in l3_devices:
        physical_interfaces = list(device.physical_interfaces())
        allocated = list(
            interface.ipv4_address for interface in physical_interfaces
            if interface.is_bound and interface['ipv4'].allocate is not False
            and interface['ipv4'].is_bound)
        if all(interface.ipv4_address for interface in
               physical_interfaces if interface.is_bound
               and interface['ip'].allocate is not False
               and interface['ip'].is_bound):
            # add as a manual allocated device
            manual_alloc_devices.add(device)

    if manual_alloc_devices == set(l3_devices):
        manual_alloc_ipv4_infrastructure = True
    else:
        log.info("Allocating from IPv4 infrastructure block: %s" % infra_block)
        manual_alloc_ipv4_infrastructure = False
        # warn if any set
        allocated = []
        unallocated = []
        for node in l3_devices:
            # TODO: make these inverse sets
            allocated += sorted([i for i in node.physical_interfaces()
                                 if i.is_bound and i.ipv4_address])
            unallocated += sorted([i for i in node.physical_interfaces()
                                   if i.is_bound and not i.ipv4_address
                                   and i['ipv4'].is_bound])

        # TODO: what if IP is set but not a prefix?
        if len(allocated):
            # TODO: if set is > 50% of nodes then list those that are NOT set
            log.warning(
                "Using automatic IPv4 interface allocation. IPv4 interface addresses specified on interfaces %s will be ignored." % allocated)

    # TODO: need to set allocate_ipv4 by default in the readers

    if manual_alloc_ipv4_infrastructure:
        manual_ipv4_infrastructure_allocation(anm)
    else:
        ipv4.allocate_infra(g_ipv4, infra_block)

    if g_in.data.alloc_ipv4_loopbacks is False:
        manual_ipv4_loopback_allocation(anm)
    else:
        log.info("Allocating from IPv4 loopback block: %s" % loopback_block)
        # Check if some nodes are allocated
        allocated = sorted([n for n in g_ip if n['input'].loopback_v4])
        unallocated = sorted([n for n in g_ip if not n['input'].loopback_v4])
        if len(allocated):
            log.warning(
                "Using automatic IPv4 loopback allocation. IPv4 loopback addresses specified on nodes %s will be ignored." % allocated)
            # TODO: if set is > 50% of nodes then list those that are NOT set
        ipv4.allocate_loopbacks(g_ipv4, loopback_block)

    # TODO: need to also support secondary_loopbacks for IPv6
    # TODO: only call if secondaries are set

    ipv4.allocate_secondary_loopbacks(g_ipv4, vrf_loopback_block)

    # TODO: replace this with direct allocation to interfaces in ip alloc plugin
    # TODO: add option for nonzero interfaces on node - ie
    # node.secondary_loopbacks
    for node in g_ipv4:
        node.static_routes = []

    for node in g_ipv4.routers():
        node.loopback_zero.ip_address = node.loopback
        node.loopback_zero.subnet = netaddr.IPNetwork("%s/32" % node.loopback)
        for interface in node.loopback_interfaces():
            if not interface.is_loopback_zero:
                # TODO: fix this inconsistency elsewhere
                interface.ip_address = interface.loopback
