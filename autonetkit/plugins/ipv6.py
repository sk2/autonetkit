#!/usr/bin/python
# -*- coding: utf-8 -*-
import json

import autonetkit.ank as ank_utils
import autonetkit.ank_json
import autonetkit.ank_messaging
import autonetkit.log as log
import netaddr

# TODO: allow slack in allocations: both for ASN (group level), and for collision domains to allow new nodes to be easily added

try:
    import cPickle as pickle
except ImportError:
    import pickle


def assign_asn_to_interasn_cds(G_ip):
    #TODO: remove this if no longer needed

    # TODO: rename to assign_asn_to_cds as also does intra-asn cds
    # TODO: make this a common function to ip4 and ip6

    G_phy = G_ip.overlay('phy')
    for broadcast_domain in G_ip.nodes('broadcast_domain'):
        neigh_asn = list(ank_utils.neigh_attr(G_ip, broadcast_domain,
                         'asn', G_phy))  # asn of neighbors
        if len(set(neigh_asn)) == 1:
            asn = set(neigh_asn).pop()  # asn of any neigh, as all same
        else:
            asn = ank_utils.most_frequent(neigh_asn)  # allocate bc to asn with most neighbors in it
        broadcast_domain.asn = asn

    return

def allocate_loopbacks(g_ip, address_block=None):
    #TODO: handle no block specified
    loopback_blocks = {}
    loopback_pool = address_block.subnet(80)

    # consume the first address as it is the network address

    loopback_network = loopback_pool.next()  # network address

    unique_asns = set(n.asn for n in g_ip)
    for asn in sorted(unique_asns):
        loopback_blocks[asn] = loopback_pool.next()

    for (asn, devices) in g_ip.groupby('asn').items():
        loopback_hosts = loopback_blocks[asn].iter_hosts()
        loopback_hosts.next()  # drop .0 as a host address (valid but can be confusing)
        l3hosts = set(d for d in devices if d.is_l3device())
        for host in sorted(l3hosts, key=lambda x: x.label):
            host.loopback = loopback_hosts.next()

    g_ip.data.loopback_blocks = dict((asn, [subnet]) for (asn,
            subnet) in loopback_blocks.items())

def allocate_infra(g_ip, address_block=None):
    infra_blocks = {}

# TODO: check if need to do network address... possibly only for loopback_pool and infra_pool so maps to asn

    infra_pool = address_block.subnet(80)

    # consume the first address as it is the network address

    infra_network = infra_pool.next()  # network address

    unique_asns = set(n.asn for n in g_ip)
    for asn in sorted(unique_asns):
        infra_blocks[asn] = infra_pool.next()

    for (asn, devices) in sorted(g_ip.groupby('asn').items()):
        subnets = infra_blocks[asn].subnet(96)
        subnets.next()  # network address
        ptp_subnet = subnets.next().subnet(126)
        ptp_subnet.next()  # network address
        all_bcs = set(d for d in devices if d.broadcast_domain)
        ptp_bcs = [bc for bc in all_bcs if bc.degree() == 2]

        for bc in sorted(ptp_bcs):
            subnet = ptp_subnet.next()
            hosts = subnet.iter_hosts()
            hosts.next()  # drop .0 as a host address (valid but can be confusing)
            bc.subnet = subnet
            #TODO: check: should sort by default on dst as tie-breaker
            for edge in sorted(bc.edges(), key=lambda x: x.dst.label):
                edge.ip = hosts.next()

        non_ptp_cds = all_bcs - set(ptp_bcs)

        # break into /96 subnets

        for bc in sorted(non_ptp_cds):
            subnet = subnets.next()
            hosts = subnet.iter_hosts()
            hosts.next()  # drop .0 as a host address (valid but can be confusing)
            bc.subnet = subnet
            for edge in sorted(bc.edges(), key=lambda x: x.dst.label):
                edge.ip = hosts.next()


    g_ip.data.infra_blocks = dict((asn, [subnet]) for (asn, subnet) in
                                  infra_blocks.items())

def allocate_vrf_loopbacks(g_ip, address_block=None):
    secondary_loopback_blocks = {}
    secondary_loopback_pool = address_block.subnet(80)
    # consume the first address as it is the network address
    secondary_loopback_network = secondary_loopback_pool.next()  # network address

    unique_asns = set(n.asn for n in g_ip)
    for asn in sorted(unique_asns):
        secondary_loopback_blocks[asn] = \
            secondary_loopback_network.next()

    for (asn, devices) in g_ip.groupby('asn').items():
        l3hosts = set(d for d in devices if d.is_l3device())
        routers = [n for n in l3hosts if n.is_router()]  # filter
        secondary_loopbacks = [i for n in routers for i in
                               n.loopback_interfaces
                               if not i.is_loopback_zero]

        secondary_loopback_hosts = \
            secondary_loopback_blocks[asn].iter_hosts()
        secondary_loopback_hosts.next()  # drop .0 as a host address (valid but can be confusing)
        for interface in sorted(secondary_loopbacks):
            interface.loopback = secondary_loopback_hosts.next()
            interface.subnet = netaddr.IPNetwork("%s/128" % interface.loopback)

def allocate_ips(G_ip, infra_block = None, loopback_block = None, secondary_loopback_block = None):
    log.info('Allocating Host loopback IPs')
    #TODO: move the following step to the l3 graph
    assign_asn_to_interasn_cds(G_ip)

    allocate_loopbacks(G_ip, loopback_block)
    allocate_infra(G_ip, infra_block)
    allocate_vrf_loopbacks(G_ip, secondary_loopback_block)