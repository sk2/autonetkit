import typing
from typing import List

from autonetkit.network_model.exceptions import NodeNotFound
from autonetkit.network_model.types import DeviceType, PortType

if typing.TYPE_CHECKING:
    from autonetkit.network_model.port import Port
    from autonetkit.network_model.node import Node
    from autonetkit.network_model.topology import Topology


def filter_nodes(topology: 'Topology', **kwargs) -> List['Node']:
    """

    @param topology:
    @param kwargs:
    @return:
    """
    result = []
    for node in topology.nodes():
        matched = all(node.get(key) == val
                      for key, val in kwargs.items())
        if matched:
            result.append(node)

    return result


def routers(topology: 'Topology') -> List['Node']:
    """

    @param topology:
    @return:
    """
    return filter_nodes(topology, type=DeviceType.ROUTER)


def switches(topology: 'Topology') -> List['Node']:
    """

    @param topology:
    @return:
    """
    return filter_nodes(topology, type=DeviceType.SWITCH)


def hosts(topology: 'Topology') -> List['Node']:
    """

    @param topology:
    @return:
    """
    return filter_nodes(topology, type=DeviceType.HOST)


def broadcast_domains(topology) -> List['Node']:
    """

    @param topology:
    @return:
    """
    return filter_nodes(topology, type=DeviceType.BROADCAST_DOMAIN)


def physical_ports(node: 'Node') -> List['Port']:
    """

    @param node:
    @return:
    """
    return [p for p in node.ports()
            if p.type == PortType.PHYSICAL]


def find_node_by_label(topology: 'Topology', label) -> 'Node':
    """

    @param topology:
    @param label:
    @return:
    """
    for node in topology.nodes():
        if node.label == label:
            return node

    raise NodeNotFound()
