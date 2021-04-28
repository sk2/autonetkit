import logging
from typing import Dict, List

from autonetkit.compile.platform.base import BasePlatformCompiler
from autonetkit.design.utils import filters
from autonetkit.network_model.exceptions import PortNotFound
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.node import Node
from autonetkit.network_model.types import DeviceType

logger = logging.getLogger(__name__)


class KatharaCompiler(BasePlatformCompiler):
    def compile(self, network_model: NetworkModel) -> Dict:
        """

        @param network_model:
        @return:
        """
        result = {}
        t_phy = network_model.get_topology("physical")

        result["nodes"] = self._compile_node_startup(network_model, t_phy)
        result["lab"] = self._compile_lab(t_phy)

        return result

    def _compile_lab(self, t_phy) -> Dict:
        result = {
            "nodes": []
        }

        for node in t_phy.nodes():
            interfaces = []
            for port in filters.physical_ports(node):
                if port.degree() > 0:
                    if port.degree() > 1:
                        logger.warning("Port %s on %s has multiple physical links: only using first",
                                       port.label, node.label)
                    # TODO: note this assumes single physical link per port
                    link = port.links()[0]
                    link_id = link.id

                    interfaces.append({
                        "slot": port.slot,
                        "link_id": link_id
                    })

            entry = {
                "label": node.label,
                "interfaces": interfaces
            }
            result["nodes"].append(entry)

        return result

    def _compile_node_startup(self, network_model, t_phy) -> List:
        result = []
        t_ipv4 = network_model.get_topology("ipv4")
        for node in t_phy.nodes():
            interfaces = []
            for port in filters.physical_ports(node):
                data = {
                    "label": port.label,
                    "connected": port.connected
                }

                if port.connected:
                    try:
                        ipv4_port = t_ipv4.get_port_by_id(port.id)
                    except PortNotFound:
                        # no ip for this port
                        continue

                    data["ip"] = ipv4_port.get("ip")
                    data["netmask"] = ipv4_port.get("network").netmask

                interfaces.append(data)

            services = {}
            if node.type == DeviceType.ROUTER:
                services["zebra"] = True

            result.append({
                "label": node.label,
                "interfaces": interfaces,
                "services": services
            })

        return result

    def compile_node(self, node: Node) -> Dict:
        """

        @param node:
        @return:
        """
        return {
            "hostname": node.label
        }
