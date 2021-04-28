import ipaddress
from collections import defaultdict

from autonetkit.design.utils import filters
from autonetkit.design.utils.general import group_by
from autonetkit.network_model.types import LAYER3_DEVICES


def assign_loopbacks(topology):
    """

    @param topology:
    """
    layer3_nodes = [n for n in topology.nodes()
                    if n.type in LAYER3_DEVICES]
    loopback_block = ipaddress.IPv4Network("172.16.0.0/16")
    loopback_subnets = loopback_block.subnets(new_prefix=24)
    grouped_l3 = group_by(layer3_nodes, "asn")

    allocated_loopbacks = defaultdict(list)

    for asn, nodes in grouped_l3.items():
        # can repeat the loopbacks in each asn
        subnet = next(loopback_subnets)
        allocated_loopbacks[asn].append(subnet)
        host_ips = subnet.hosts()
        for node in nodes:
            host_ip = next(host_ips)
            lo0 = node.loopback_zero()
            lo0.set("ip", host_ip)
            # also map onto node for debugging/vis

    topology.set("loopbacks_by_asn", allocated_loopbacks)


def assign_bc_subnets(topology):
    """

    @param topology:
    """
    # the network to use to address end hosts and for inter-domain connections
    allocated_blocks = defaultdict(list)
    global_advertise_network = ipaddress.IPv4Network("10.0.0.0/8")
    global_subnets = global_advertise_network.subnets(new_prefix=16)
    bc_nodes = filters.broadcast_domains(topology)
    grouped_bc = group_by(bc_nodes, "asn")
    for asn, nodes in grouped_bc.items():
        asn_block = next(global_subnets)
        allocated_blocks[asn].append(asn_block)
        # quick method: allocate a /24 to each broadcast domain
        # Note: this could be significantly optimised in the future
        # Note: could allocate different block to internal infrastructure too
        external_blocks = asn_block.subnets(new_prefix=24)
        for bc in nodes:
            bc_block = next(external_blocks)
            bc.set("network", bc_block)
    topology.set("infrastructure_by_asn", allocated_blocks)
