import time
from collections import defaultdict
import json
import itertools
import pprint
import math
import os
import autonetkit.ank as ank_utils
import autonetkit.log as log
import autonetkit.messaging
import autonetkit.ank_json
import networkx as nx
from collections import defaultdict
import netaddr
import functools

settings = autonetkit.config.settings
rabbitmq_server = settings['Rabbitmq']['server']
messaging = autonetkit.ank_messaging.AnkMessaging(rabbitmq_server)

#TODO: allow slack in allocations: both for ASN (group level), and for collision domains to allow new nodes to be easily added

try:
    import cPickle as pickle
except ImportError:
    import pickle

def assign_asn_to_interasn_cds(G_ip):
    #TODO: rename to assign_asn_to_cds as also does intra-asn cds
    #TODO: make this a common function to ip4 and ip6
    G_phy = G_ip.overlay.phy
    for collision_domain in G_ip.nodes("collision_domain"):
        neigh_asn = list(ank_utils.neigh_attr(G_ip, collision_domain, "asn", G_phy)) #asn of neighbors
        if len(set(neigh_asn)) == 1:
            asn = set(neigh_asn).pop() # asn of any neigh, as all same
        else:
            asn = ank_utils.most_frequent(neigh_asn) # allocate cd to asn with most neighbors in it
        collision_domain.asn = asn

    return

def allocate_ips(G_ip):
    log.info("Allocating Host loopback IPs")

# assign a /64 to each asn
    assign_asn_to_interasn_cds(G_ip)

    loopback_blocks = {}
    infra_blocks = {}

#TODO: check if need to do network address... possibly only for loopback_pool and infra_pool so maps to asn

    global_pool = netaddr.IPNetwork("2001:db8::/32").subnet(48)
    global_pool = netaddr.IPNetwork("::/32").subnet(64)
    global_pool.next() # network address
    [global_pool.next() for i in range(9)] # consume generator to start infra at "a", loopbacks at "b"
    loopback_pool = global_pool.next().subnet(80)
    infra_pool = global_pool.next().subnet(80)

    loopback_pool.next() # network address
    infra_pool.next() # network address

    unique_asns = set(n.asn for n in G_ip)
    for asn in sorted(unique_asns):
        loopback_blocks[asn] = loopback_pool.next()
        infra_blocks[asn] = infra_pool.next()

    for asn, devices in G_ip.groupby("asn").items():
        print asn, infra_blocks[asn]
        subnets = infra_blocks[asn].subnet(96)
        subnets.next() # network address
        ptp_subnet = subnets.next().subnet(126)
        ptp_subnet.next() # network address
        all_cds = set(d for d in devices if d.collision_domain)
        ptp_cds = [cd for cd in all_cds if cd.degree() == 2]

        for cd in ptp_cds:
            subnet = ptp_subnet.next()
            hosts = subnet.iter_hosts()
            hosts.next() # drop .0 as a host address (valid but can be confusing)
            cd.subnet = subnet 
            for edge in cd.edges():
                edge.ip = hosts.next()

        non_ptp_cds = all_cds - set(ptp_cds)
        # break into /96 subnets
        for cd in non_ptp_cds:
            subnet = subnets.next()
            hosts = subnet.iter_hosts()
            hosts.next() # drop .0 as a host address (valid but can be confusing)
            cd.subnet = subnet 
            for edge in cd.edges():
                edge.ip = hosts.next()


        loopback_hosts = loopback_blocks[asn].iter_hosts()
        loopback_hosts.next() # drop .0 as a host address (valid but can be confusing)
        l3hosts = set(d for d in devices if d.is_l3device)
        for host in l3hosts:
            host.loopback = loopback_hosts.next()

    # Store allocations for routing advertisement
    G_ip.data.infra_blocks = infra_blocks
    G_ip.data.loopback_blocks = loopback_blocks

    print "done"




#TODO: need to update with loopbacks if wish to advertise also - or subdivide blocks?

    #ip_tree.save()
