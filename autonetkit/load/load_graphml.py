from collections import defaultdict

import networkx as nx

from autonetkit.load.common import normalise_node_locations, add_loopback
from autonetkit.load.model import StructuredNode, StructuredPort, StructuredTopology, StructuredLink
from autonetkit.load.preprocess import process_structured_topology
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.types import PortType, DeviceType


def import_from_graphml(filename: str) -> NetworkModel:
    """

    @param filename:
    @return:
    """
    network_model = NetworkModel()
    with open(filename) as fh:
        graph = nx.read_graphml(fh)

    node_map = {}
    node_port_map = defaultdict(dict)

    topology = StructuredTopology()

    for nx_node_id, node_data in graph.nodes(data=True):
        label = node_data.get("label").strip()

        # create loopback zero
        device_type = node_data.get("device_type").title()
        get = node_data.get("x")
        node = StructuredNode(type=device_type,
                              label=label,
                              x=get,
                              y=node_data.get("y"),
                              asn=node_data.get("asn"),
                              target=node_data.get("target"),
                              )

        topology.nodes.append(node)
        node_map[nx_node_id] = node

        if node.type in {DeviceType.ROUTER, DeviceType.HOST}:
            add_loopback(node)

        edges = [data for _, _, data in graph.in_edges(nx_node_id, data=True)]
        edges += [data for _, _, data in graph.out_edges(nx_node_id, data=True)]
        for slot, edge_data in enumerate(edges):
            port = StructuredPort(type=PortType.PHYSICAL, slot=slot)
            node.ports.append(port)
            edge_id = edge_data["id"]
            node_port_map[nx_node_id][edge_id] = port

    for src, dst, node_data in graph.edges(data=True):
        edge_id = node_data["id"]
        n1 = node_map[src].label
        n2 = node_map[dst].label
        p1 = node_port_map[src][edge_id].slot
        p2 = node_port_map[dst][edge_id].slot
        link = StructuredLink(n1=n1, n2=n2, p1=p1, p2=p2)
        topology.links.append(link)

    # TODO: later match this to the YAML physical inventory etc
    network_model = process_structured_topology(topology)
    t_in = network_model.get_topology("input")

    normalise_node_locations(t_in)

    # and reset network model ids in use

    return network_model
