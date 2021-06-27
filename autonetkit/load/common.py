import typing
from collections import defaultdict

import networkx as nx

from autonetkit.design.utils import filters
from autonetkit.load.model import StructuredTopology, StructuredNode, StructuredPort, StructuredLink
from autonetkit.load.preprocess import process_structured_topology
from autonetkit.load.simplified import SimplifiedTopology
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.topology import Topology
from autonetkit.network_model.types import DeviceType, PortType, LAYER3_DEVICES


def label_physical_ports(topology: Topology, port_prefix) -> None:
    """

    @param topology:
    @param port_prefix:
    """
    # TODO: later can skip this step if assigned by user
    for node in topology.nodes():
        physical_ports = filters.physical_ports(node)
        for index, port in enumerate(physical_ports):
            port.set("label", f"{port_prefix}{index}")
            port.set("slot", index)


def build_model_from_nx_graph(graph: typing.Union[nx.Graph, nx.DiGraph]) -> NetworkModel:
    """

    @param graph:
    @return: 
    """
    raw_topology = {"nodes": [], "links": []}
    for nid in graph.nodes():
        raw_topology["nodes"].append({
            "id": nid,
            "label": f"r{nid}"
        })

    for src, dst in graph.edges():
        pair = (f"r{src}", f"r{dst}")
        raw_topology["links"].append(pair)

    simplified_topology = SimplifiedTopology(**raw_topology)
    topology = transform_simplified_to_structured_topology(simplified_topology)
    network_model = process_structured_topology(topology)

    return network_model


def transform_simplified_to_structured_topology(simplified_topology):
    """

    @param simplified_topology: 
    @return: 
    """
    for node in simplified_topology.nodes:
        if node.type is None:
            node.type = DeviceType.ROUTER

    topology = StructuredTopology()
    node_map = {}
    port_map = defaultdict(int)
    for simplified_node in simplified_topology.nodes:
        structured_node = StructuredNode(**simplified_node.dict())
        node_map[simplified_node.label] = structured_node
        if structured_node.type in LAYER3_DEVICES:
            port = StructuredPort(type=PortType.LOGICAL, loopback_zero=True)
            structured_node.ports.append(port)

        topology.nodes.append(structured_node)
    for simplified_link in simplified_topology.links:
        n1_label = simplified_link[0]
        n2_label = simplified_link[1]
        n1 = node_map[n1_label]
        n2 = node_map[n2_label]
        slot1 = port_map[n1_label]
        slot2 = port_map[n2_label]
        port_map[n1_label] += 1
        port_map[n2_label] += 2

        p1 = StructuredPort(type=PortType.PHYSICAL, slot=slot1)
        n1.ports.append(p1)
        p2 = StructuredPort(type=PortType.PHYSICAL, slot=slot2)
        n2.ports.append(p2)

        link = StructuredLink(n1=n1_label, n2=n2_label, p1=slot1, p2=slot2)
        topology.links.append(link)
    return topology


def add_loopback(node):
    """

    @param node: 
    """
    port = StructuredPort(type=PortType.LOGICAL, loopback_zero=True)
    node.ports.append(port)
