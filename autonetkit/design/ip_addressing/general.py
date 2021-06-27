from collections import Counter
from enum import Enum

from autonetkit.design.utils import filters
from autonetkit.network_model.base.network_model import NetworkModel
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.topology import Topology
from autonetkit.network_model.base.types import DeviceType


def build_ip_base(network_model: NetworkModel, topology: Topology):
    """

    @param network_model:
    @param topology:
    """
    t_l2 = network_model.get_topology("layer2")
    topology.add_nodes_from(t_l2.nodes())
    topology.add_links_from(t_l2.links())

    bc_nodes = filters.broadcast_domains(topology)

    for node in bc_nodes:
        peers = node.peer_nodes()
        peer_asns = {n.get("asn") for n in peers}
        peer_types = {n.type for n in peers}
        if len(peer_asns) == 1:
            if peer_types == {DeviceType.ROUTER}:
                node.set("bc_type", IpBcTypes.BACKBONE)
            else:
                node.set("bc_type", IpBcTypes.HOSTS)

        else:
            node.set("bc_type", IpBcTypes.INTER_DOMAIN)


def allocate_asns(topology: Topology):
    """

    @param topology:
    """
    bc_nodes = filters.broadcast_domains(topology)

    for node in bc_nodes:
        peer_asns = sorted(n.get("asn") for n in node.peer_nodes())
        if len(set(peer_asns)) == 1:
            asn = peer_asns[0]
        else:
            counted = Counter(peer_asns)
            asn = counted.most_common(1)[0][0]
        node.set("asn", asn)


def _sort_ports_by_routers(port: Port):
    # sorts so that routers are allocated the first ip from block
    if port.node.type == DeviceType.ROUTER:
        return 1
    else:
        return 2


def map_blocks_to_ports(topology):
    """

    @param topology:
    """
    bc_nodes = filters.broadcast_domains(topology)
    for bc_node in bc_nodes:
        subnet = bc_node.get("network")
        hosts = subnet.hosts()
        ports = bc_node.peer_ports()
        ports = sorted(ports, key=lambda x: _sort_ports_by_routers(x))
        for peer_port in ports:
            peer_port.set("network", subnet)
            host_ip = next(hosts)
            peer_port.set("ip", host_ip)


class IpBcTypes(Enum):
    HOSTS = 1
    BACKBONE = 2
    INTER_DOMAIN = 3
