#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.ank as ank_utils
import autonetkit.config
import autonetkit.log as log
from autonetkit.ank_utils import call_log

SETTINGS = autonetkit.config.settings


@call_log
def manual_ipv6_loopback_allocation(anm):
    """Applies manual IPv6 allocation"""

    import netaddr
    g_ipv6 = anm['ipv6']

    for l3_device in g_ipv6.l3devices():
        l3_device.loopback = l3_device['input'].loopback_v6

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)

    loopback_blocks = {}
    for (asn, devices) in g_ipv6.groupby('asn').items():
        routers = [d for d in devices if d.is_router()]
        loopbacks = [r.loopback for r in routers]
        loopback_blocks[asn] = netaddr.cidr_merge(loopbacks)

    g_ipv6.data.loopback_blocks = loopback_blocks

@call_log
def extract_ipv6_blocks(anm):

    # TODO: set all these blocks globally in config file, rather than repeated in load, build_network, compile, etc

    from autonetkit.ank import sn_preflen_to_network
    from netaddr import IPNetwork
    g_in = anm['input']

    ipv6_defaults = SETTINGS["IP Addressing"]["v6"]

    try:
        infra_subnet = g_in.data.ipv6_infra_subnet
        infra_prefix = g_in.data.ipv6_infra_prefix
        infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        infra_block = IPNetwork('%s/%s' % (ipv6_defaults["infra_subnet"], ipv6_defaults["infra_prefix"]))
        if infra_subnet is None or infra_prefix is None:
            log.debug('Using default IPv6 infra_subnet %s'% infra_block)
        else:
            log.warning('Unable to obtain IPv6 infra_subnet from input graph: %s, using default %s'% (e, infra_block))

    try:
        loopback_subnet = g_in.data.ipv6_loopback_subnet
        loopback_prefix = g_in.data.ipv6_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                loopback_prefix)
    except Exception, e:
        loopback_block = IPNetwork('%s/%s' % (ipv6_defaults["loopback_subnet"], ipv6_defaults["loopback_prefix"]))
        if loopback_subnet is None or loopback_prefix is None:
            log.debug('Using default IPv6 loopback_subnet %s'% loopback_block)
        else:
            log.warning('Unable to obtain IPv6 loopback_subnet from input graph: %s, using default %s'% (e, loopback_block))

    try:
        vrf_loopback_subnet = g_in.data.ipv6_vrf_loopback_subnet
        vrf_loopback_prefix = g_in.data.ipv6_vrf_loopback_prefix
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet,
                vrf_loopback_prefix)
    except Exception, e:
        vrf_loopback_block = IPNetwork('%s/%s' % (ipv6_defaults["vrf_loopback_subnet"], ipv6_defaults["vrf_loopback_prefix"]))
        if vrf_loopback_subnet is None or vrf_loopback_prefix is None:
            log.debug('Using default IPv6 vrf_loopback_subnet %s'% vrf_loopback_block)
        else:
            log.warning('Unable to obtain IPv6 vrf_loopback_subnet from input graph: %s, using default %s'% (e, vrf_loopback_block))

    return (infra_block, loopback_block, vrf_loopback_block)

@call_log
def manual_ipv6_infrastructure_allocation(anm):
    """Applies manual IPv6 allocation"""

    import netaddr
    g_ipv6 = anm['ipv6']
    log.info('Using specified IPv6 infrastructure allocation')

    for node in g_ipv6.l3devices():
        for interface in node.physical_interfaces:
            if not interface['input'].is_bound:
                continue  # unbound interface
            ip_address = netaddr.IPAddress(interface['input'
                    ].ipv6_address)
            prefixlen = interface['input'].ipv6_prefixlen
            interface.ip_address = ip_address
            interface.prefixlen = prefixlen
            cidr_string = '%s/%s' % (ip_address, prefixlen)
            interface.subnet = netaddr.IPNetwork(cidr_string)

    broadcast_domains = [d for d in g_ipv6 if d.broadcast_domain]

    # TODO: allow this to work with specified ip_address/subnet as well as ip_address/prefixlen

    from netaddr import IPNetwork
    for coll_dom in broadcast_domains:
        connected_interfaces = [edge.dst_int for edge in
                                coll_dom.edges()]
        cd_subnets = [IPNetwork('%s/%s' % (i.subnet.network,
                      i.prefixlen)) for i in connected_interfaces]


        if len(cd_subnets) == 0:
            log.warning("Collision domain %s is not connected to any nodes" % coll_dom)
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
    # autonetkit.update_http(anm)

    infra_blocks = {}
    for (asn, devices) in g_ipv6.groupby('asn').items():
        broadcast_domains = [d for d in devices if d.broadcast_domain]
        subnets = [cd.subnet for cd in broadcast_domains
        if cd.subnet is not None] # only if subnet is set
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    g_ipv6.data.infra_blocks = infra_blocks

@call_log
def build_ipv6(anm):
    """Builds IPv6 graph, using nodes and edges from IP graph"""
    import netaddr
    import autonetkit.plugins.ipv6 as ipv6

    # uses the nodes and edges from ipv4

    g_ipv6 = anm.add_overlay('ipv6')
    g_ip = anm['ip']
    g_in = anm['input']
    g_ipv6.add_nodes_from(g_ip, retain=['label', 'asn', 'broadcast_domain'])  # retain if collision domain or not
    g_ipv6.add_edges_from(g_ip.edges())

    #TODO: tidy up naming consitency of secondary_loopback_block and vrf_loopback_block
    (infra_block, loopback_block, secondary_loopback_block) = \
        extract_ipv6_blocks(anm)

    block_message = "IPv6 allocations: Infrastructure: %s, Loopback: %s" % (infra_block, loopback_block)
    if any(i for n in g_ip.nodes() for i in
     n.loopback_interfaces if not i.is_loopback_zero):
        block_message += " Secondary Loopbacks: %s" % secondary_loopback_block
    log.info(block_message)

    # TODO: replace this with direct allocation to interfaces in ip alloc plugin
    allocated = sorted([n for n in g_ip if n['input'].loopback_v6])
    if len(allocated) == len(g_ip.l3devices()):
        # all allocated
        #TODO: need to infer subnetomanual_ipv6_loopback_allocation
        log.info("Using user-specified IPv6 loopback addresses")
        manual_ipv6_loopback_allocation(anm)
    else:
        if len(allocated):
            log.warning("Using automatic IPv6 loopback allocation. IPv6 loopback addresses specified on nodes %s will be ignored." % allocated)
        else:
            log.info("Automatically assigning IPv6 loopback addresses")

        ipv6.allocate_loopbacks(g_ipv6, loopback_block)

    l3_devices = [d for d in g_in if d.device_type in ('router', 'server')]

    manual_alloc_devices = set()
    for device in l3_devices:
        physical_interfaces = list(device.physical_interfaces)
        allocated = list(interface.ipv6_address for interface in physical_interfaces if interface.is_bound)
        if all(interface.ipv6_address for interface in
               physical_interfaces if interface.is_bound):
            manual_alloc_devices.add(device)  # add as a manual allocated device

    if manual_alloc_devices == set(l3_devices):
        log.info("Using user-specified IPv6 infrastructure addresses")
        manual_alloc_ipv6_infrastructure = True
    else:
        manual_alloc_ipv6_infrastructure = False
        # warn if any set
        allocated = []
        unallocated = []
        for node in l3_devices:
            allocated += sorted([i for i in node.physical_interfaces if i.is_bound and i.ipv6_address])
            unallocated += sorted([i for i in node.physical_interfaces if i.is_bound and not i.ipv6_address])

        #TODO: what if IP is set but not a prefix?
        if len(allocated):
            #TODO: if set is > 50% of nodes then list those that are NOT set
            log.warning("Using automatic IPv6 interface allocation. IPv6 interface addresses specified on interfaces %s will be ignored." % allocated)
        else:
            log.info("Automatically assigning IPv6 infrastructure addresses")

    if manual_alloc_ipv6_infrastructure:
        manual_ipv6_infrastructure_allocation(anm)
    else:
        ipv6.allocate_infra(g_ipv6, infra_block)
        #TODO: see if this is still needed or if can allocate direct from the ipv6 allocation plugin
        for node in g_ipv6.l3devices():
            for interface in node:
                edges = list(interface.edges())
                if len(edges):
                    edge = edges[0]  # first (only) edge
                    interface.ip_address = edge.ip  # TODO: make this consistent
                    interface.subnet = edge.dst.subnet  # from collision domain

    ipv6.allocate_vrf_loopbacks(g_ipv6, secondary_loopback_block)

    for node in g_ipv6.routers():
        #TODO: test this code
        node.loopback_zero.ip_address = node.loopback
        node.loopback_zero.subnet = netaddr.IPNetwork("%s/32" % node.loopback)
        for interface in node.loopback_interfaces:
            if not interface.is_loopback_zero:
                interface.ip_address = interface.loopback #TODO: fix this inconsistency elsewhere

@call_log
def manual_ipv4_infrastructure_allocation(anm):
    """Applies manual IPv4 allocation"""

    import netaddr
    g_ipv4 = anm['ipv4']
    log.info('Using specified IPv4 infrastructure allocation')

    for node in g_ipv4.l3devices():
        for interface in node.physical_interfaces:
            if not interface['input'].is_bound:
                continue  # unbound interface
            ip_address = netaddr.IPAddress(interface['input'
                    ].ipv4_address)
            prefixlen = interface['input'].ipv4_prefixlen
            interface.ip_address = ip_address
            interface.prefixlen = prefixlen
            cidr_string = '%s/%s' % (ip_address, prefixlen)
            interface.subnet = netaddr.IPNetwork(cidr_string)

    broadcast_domains = [d for d in g_ipv4 if d.broadcast_domain]

    # TODO: allow this to work with specified ip_address/subnet as well as ip_address/prefixlen

    from netaddr import IPNetwork
    for coll_dom in broadcast_domains:
        #TODO: add neighbor_ints to API?
        connected_interfaces = [edge.dst_int for edge in
                                coll_dom.edges()]

        connected_interfaces = [i for i in connected_interfaces
            if i.node.is_l3device()]

        cd_subnets = [IPNetwork('%s/%s' % (i.subnet.network,
                      i.prefixlen)) for i in connected_interfaces]

        if len(cd_subnets) == 0:
            log.warning("Collision domain %s is not connected to any nodes" % coll_dom)
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
    # autonetkit.update_http(anm)

    infra_blocks = {}
    for (asn, devices) in g_ipv4.groupby('asn').items():
        broadcast_domains = [d for d in devices if d.broadcast_domain]
        subnets = [cd.subnet for cd in broadcast_domains
        if cd.subnet is not None] # only if subnet is set
        infra_blocks[asn] = netaddr.cidr_merge(subnets)

    g_ipv4.data.infra_blocks = infra_blocks


@call_log
def manual_ipv4_loopback_allocation(anm):
    """Applies manual IPv4 allocation"""

    import netaddr
    g_ipv4 = anm['ipv4']

    for l3_device in g_ipv4.l3devices():
        l3_device.loopback = l3_device['input'].loopback_v4

    # also need to form aggregated IP blocks (used for e.g. routing prefix
    # advertisement)

    loopback_blocks = {}
    for (asn, devices) in g_ipv4.groupby('asn').items():
        routers = [d for d in devices if d.is_router()]
        loopbacks = [r.loopback for r in routers]
        loopback_blocks[asn] = netaddr.cidr_merge(loopbacks)

    g_ipv4.data.loopback_blocks = loopback_blocks


@call_log
def build_ip(anm):
    #TODO: use the l3_conn graph
    g_ip = anm.add_overlay('ip')
    g_in = anm['input']
    g_graphics = anm['graphics']
    g_phy = anm['phy']

    #TODO: add these from layer2 graph - and scrap g_ip: clone g_layer2 to g_ipv4 and g_ipv6
    g_ip.add_nodes_from(g_phy)
    g_ip.add_edges_from(g_phy.edges())

    ank_utils.aggregate_nodes(g_ip, g_ip.switches())

    edges_to_split = [edge for edge in g_ip.edges()
        if edge.src.is_l3device() and edge.dst.is_l3device()]
    for edge in edges_to_split:
        edge.split = True  # mark as split for use in building nidb

    split_created_nodes = list(ank_utils.split(g_ip, edges_to_split,
                               retain=['split'],
                               id_prepend='cd'))
    for node in split_created_nodes:
        node['graphics'].x = ank_utils.neigh_average(g_ip, node, 'x',
                g_graphics) + 0.1

         # temporary fix for gh-90

        node['graphics'].y = ank_utils.neigh_average(g_ip, node, 'y',
                g_graphics) + 0.1

            # temporary fix for gh-90

        asn = ank_utils.neigh_most_frequent(g_ip, node, 'asn', g_phy)  # arbitrary choice
        node['graphics'].asn = asn
        node.asn = asn  # need to use asn in IP overlay for aggregating subnets

    switch_nodes = g_ip.switches()  # regenerate due to aggregated
    g_ip.update(switch_nodes, broadcast_domain=True)

                 # switches are part of collision domain

    g_ip.update(split_created_nodes, broadcast_domain=True)

# Assign collision domain to a host if all neighbours from same host

    for node in split_created_nodes:
        if ank_utils.neigh_equal(g_ip, node, 'host', g_phy):
            node.host = ank_utils.neigh_attr(g_ip, node, 'host',
                    g_phy).next()  # first attribute

    # set collision domain IPs
    #TODO; work out why this throws a json exception
    #autonetkit.ank.set_node_default(g_ip,  broadcast_domain=False)

    for node in g_ip.nodes('broadcast_domain'):
        graphics_node = g_graphics.node(node)
        #graphics_node.device_type = 'broadcast_domain'
        if node.is_switch():
            node['phy'].broadcast_domain = True
        if not node.is_switch():
            # use node sorting, as accomodates for numeric/string names
            graphics_node.device_type = 'broadcast_domain'
            neighbors = sorted(neigh for neigh in node.neighbors())
            label = '_'.join(neigh.label for neigh in neighbors)
            cd_label = 'cd_%s' % label  # switches keep their names
            node.label = cd_label
            node.cd_id = cd_label
            graphics_node.label = cd_label
            node.device_type = "broadcast_domain"

@call_log
def extract_ipv4_blocks(anm):

    # TODO: set all these blocks globally in config file, rather than repeated in load, build_network, compile, etc

    from autonetkit.ank import sn_preflen_to_network
    from netaddr import IPNetwork
    g_in = anm['input']
    ipv4_defaults = SETTINGS["IP Addressing"]["v4"]


    #TODO: wrap these in a common function

    try:
        infra_subnet = g_in.data.ipv4_infra_subnet
        infra_prefix = g_in.data.ipv4_infra_prefix
        infra_block = sn_preflen_to_network(infra_subnet, infra_prefix)
    except Exception, e:
        infra_block = IPNetwork('%s/%s' % (ipv4_defaults["infra_subnet"], ipv4_defaults["infra_prefix"]))
        if infra_subnet is None or infra_prefix is None:
            log.debug('Using default IPv4 infra_subnet %s'% infra_block)
        else:
            log.warning('Unable to obtain IPv4 infra_subnet from input graph: %s, using default %s'% (e, infra_block))

    try:
        loopback_subnet = g_in.data.ipv4_loopback_subnet
        loopback_prefix = g_in.data.ipv4_loopback_prefix
        loopback_block = sn_preflen_to_network(loopback_subnet,
                loopback_prefix)
    except Exception, e:
        loopback_block = IPNetwork('%s/%s' % (ipv4_defaults["loopback_subnet"], ipv4_defaults["loopback_prefix"]))
        if loopback_subnet is None or loopback_prefix is None:
            log.debug('Using default IPv4 loopback_subnet %s'% loopback_block)
        else:
            log.warning('Unable to obtain IPv4 loopback_subnet from input graph: %s, using default %s'% (e, loopback_block))

    try:
        vrf_loopback_subnet = g_in.data.ipv4_vrf_loopback_subnet
        vrf_loopback_prefix = g_in.data.ipv4_vrf_loopback_prefix
        vrf_loopback_block = sn_preflen_to_network(vrf_loopback_subnet,
                vrf_loopback_prefix)
    except Exception, e:
        vrf_loopback_block = IPNetwork('%s/%s' % (ipv4_defaults["vrf_loopback_subnet"], ipv4_defaults["vrf_loopback_prefix"]))
        if vrf_loopback_subnet is None or vrf_loopback_prefix is None:
            log.debug('Using default IPv4 vrf_loopback_subnet %s'% vrf_loopback_block)
        else:
            log.warning('Unable to obtain IPv4 vrf_loopback_subnet from input graph: %s, using default %s'% (e, vrf_loopback_block))

    return (infra_block, loopback_block, vrf_loopback_block)


@call_log
def build_ipv4(anm, infrastructure=True):
    """Builds IPv4 graph"""

    import autonetkit.plugins.ipv4 as ipv4
    import netaddr
    g_ipv4 = anm.add_overlay('ipv4')
    g_ip = anm['ip']
    g_in = anm['input']
    g_ipv4.add_nodes_from(g_ip, retain=['label', 'broadcast_domain'])  # retain if collision domain or not

    # Copy ASN attribute chosen for collision domains (used in alloc algorithm)

    ank_utils.copy_attr_from(g_ip, g_ipv4, 'asn',
                             nbunch=g_ipv4.nodes('broadcast_domain'))
    g_ipv4.add_edges_from(g_ip.edges())

    # check if ip ranges have been specified on g_in

    (infra_block, loopback_block, vrf_loopback_block) = \
        extract_ipv4_blocks(anm)

#TODO: don't present if using manual allocation
    block_message = "IPv4 allocations: Infrastructure: %s, Loopback: %s" % (infra_block, loopback_block)
    if any(i for n in g_ip.nodes() for i in
     n.loopback_interfaces if not i.is_loopback_zero):
        block_message += " Secondary Loopbacks: %s" % vrf_loopback_block

    log.info(block_message)

    # See if IP addresses specified on each interface

    # do we need this still? in ANM? - differnt because input graph.... but can map back to  self overlay first then phy???
    l3_devices = [d for d in g_in if d.device_type in ('router', 'server')]

    manual_alloc_devices = set()
    for device in l3_devices:
        physical_interfaces = list(device.physical_interfaces)
        allocated = list(interface.ipv4_address for interface in physical_interfaces if interface.is_bound)
        if all(interface.ipv4_address for interface in
               physical_interfaces if interface.is_bound):
            manual_alloc_devices.add(device)  # add as a manual allocated device

    if manual_alloc_devices == set(l3_devices):
        manual_alloc_ipv4_infrastructure = True
    else:
        manual_alloc_ipv4_infrastructure = False
        # warn if any set
        allocated = []
        unallocated = []
        for node in l3_devices:
            allocated += sorted([i for i in node.physical_interfaces if i.is_bound and i.ipv4_address])
            unallocated += sorted([i for i in node.physical_interfaces if i.is_bound and not i.ipv4_address])

        #TODO: what if IP is set but not a prefix?
        if len(allocated):
            #TODO: if set is > 50% of nodes then list those that are NOT set
            log.warning("Using automatic IPv4 interface allocation. IPv4 interface addresses specified on interfaces %s will be ignored." % allocated)

    # TODO: need to set allocate_ipv4 by default in the readers

    if manual_alloc_ipv4_infrastructure:
        manual_ipv4_infrastructure_allocation(anm)
    else:
        ipv4.allocate_infra(g_ipv4, infra_block)

    if g_in.data.alloc_ipv4_loopbacks is False:
        manual_ipv4_loopback_allocation(anm)
    else:
        # Check if some nodes are allocated
        allocated = sorted([n for n in g_ip if n['input'].loopback_v4])
        unallocated = sorted([n for n in g_ip if not n['input'].loopback_v4])
        if len(allocated):
            log.warning("Using automatic IPv4 loopback allocation. IPv4 loopback addresses specified on nodes %s will be ignored." % allocated)
            #TODO: if set is > 50% of nodes then list those that are NOT set
        ipv4.allocate_loopbacks(g_ipv4, loopback_block)

    # TODO: need to also support secondary_loopbacks for IPv6
    # TODO: only call if secondaries are set

    ipv4.allocate_vrf_loopbacks(g_ipv4, vrf_loopback_block)

    # TODO: replace this with direct allocation to interfaces in ip alloc plugin
    #TODO: add option for nonzero interfaces on node - ie node.secondary_loopbacks

    for node in g_ipv4.routers():
        node.loopback_zero.ip_address = node.loopback
        node.loopback_zero.subnet = netaddr.IPNetwork("%s/32" % node.loopback)
        for interface in node.loopback_interfaces:
            if not interface.is_loopback_zero:
                interface.ip_address = interface.loopback #TODO: fix this inconsistency elsewhere
