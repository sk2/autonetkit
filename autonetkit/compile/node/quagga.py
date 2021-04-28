from typing import Dict, List

from autonetkit.compile.node.base import BaseCompiler
from autonetkit.design.utils import filters
from autonetkit.network_model.exceptions import NodeNotFound
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.node import Node


class QuaggaCompiler(BaseCompiler):
    """

    """

    def __init__(self):
        super().__init__()

        # TODO: assign this at topology load time in pre-process step
        self.lo0_id = "lo:1"

    def compile(self, network_model: NetworkModel, node: Node) -> Dict:
        """

        @param network_model:
        @param node:
        @return:
        """
        # ensure node is from phy
        t_phy = network_model.get_topology("physical")
        node = t_phy.get_node_by_id(node.id)

        result = {}

        result["zebra"] = self._zebra(node)
        result["interfaces"] = self._interfaces(network_model, node)
        result["ospf"] = self._ospf(network_model, node)
        result["bgp"] = self._bgp(network_model, node)

        return result

    def _zebra(self, node):
        return {
            "hostname": node.label,
            "password": "zebra",
            "enable_password": "zebra",
        }

    def _interfaces(self, network_model: NetworkModel, node: Node) -> List:
        result = []

        t_ipv4 = network_model.get_topology("ipv4")

        physical_ports = filters.physical_ports(node)
        logical_ports = [p for p in node.ports()
                         if p not in physical_ports]

        physical_ports.sort(key=lambda x: x.label)
        logical_ports.sort(key=lambda x: x.label)
        for port in physical_ports:
            try:
                description = port.peer_ports()[0].node.label
            except IndexError:
                description = ""

            data = {
                "label": port.label,
                "description": description,
                "connected": port.connected
            }

            if port.connected:
                ipv4_port = t_ipv4.get_port_by_id(port.id)
                data["broadcast"] = ipv4_port.get("network").broadcast_address
                data["network"] = ipv4_port.get("network").network_address
                data["ip"] = ipv4_port.get("ip")

            result.append(data)

        return result

    def _ospf(self, network_model: NetworkModel, node: Node) -> Dict:
        t_ospf = network_model.get_topology("ospf")
        try:
            ospf_node = t_ospf.get_node_by_id(node.id)
        except NodeNotFound:
            # ospf not configured for this node
            return {}

        result = {}
        asn = node.get("asn")
        t_ipv4 = network_model.get_topology("ipv4")

        infrastructure_blocks = t_ipv4.get("infrastructure_by_asn").get(asn) or []
        networks = []
        for network in infrastructure_blocks:
            networks.append({
                "network": network.network_address,
                "area": ospf_node.get("area")
            })

        result["networks"] = networks

        return result

    def _bgp(self, network_model: NetworkModel, node: Node) -> Dict:
        result = {}
        asn = node.get("asn")
        result["asn"] = asn

        t_ipv4 = network_model.get_topology("ipv4")
        ipv4_node = t_ipv4.get_node_by_id(node.id)
        lo0_ipv4_address = ipv4_node.loopback_zero().get("ip")

        infrastructure_blocks = t_ipv4.get("infrastructure_by_asn").get(asn) or []

        result["networks"] = infrastructure_blocks

        t_ibgp = network_model.get_topology("ibgp")
        ibgp_node = t_ibgp.get_node_by_id(node.id)

        ibgp_neighbors = []
        for peer_port in ibgp_node.peer_ports():
            peer_node = peer_port.node
            peer_ip_port = t_ipv4.get_port_by_id(peer_port.id)
            peer_ipv4 = peer_ip_port.get("ip")
            neighbor = f"{peer_port.label}.{peer_node.label}"
            description = "link to " + neighbor
            ibgp_neighbors.append({
                "update_source": lo0_ipv4_address,
                "desc": neighbor,
                "asn": peer_node.get("asn"),
                "neigh_ip": peer_ipv4,
                "neighbor": neighbor,
                "description": description
            })

        result["ibgp_neighbors"] = ibgp_neighbors

        t_ebgp = network_model.get_topology("ebgp")
        ebgp_node = t_ebgp.get_node_by_id(node.id)

        ebgp_neighbors = []
        for peer_port in ebgp_node.peer_ports():
            peer_node = peer_port.node
            peer_ip_port = t_ipv4.get_port_by_id(peer_port.id)
            peer_ipv4 = peer_ip_port.get("ip")
            neighbor = f"{peer_port.label}.{peer_node.label}"
            description = "link to " + neighbor
            ebgp_neighbors.append({
                "update_source": lo0_ipv4_address,
                "desc": neighbor,
                "asn": peer_node.get("asn"),
                "neigh_ip": peer_ipv4,
                "neighbor": neighbor,
                "description": description
            })

        result["ebgp_neighbors"] = ebgp_neighbors

        return result
