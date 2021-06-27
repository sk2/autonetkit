import logging
import typing
from typing import Optional, List, NamedTuple

import networkx as nx

from autonetkit.network_model.types import DeviceType, PortType, NodeId

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from autonetkit.network_model.node import Node
    from autonetkit.network_model.port import Port
    from autonetkit.network_model.link import Link
    from autonetkit.network_model.topology import Topology


class BoundaryData(NamedTuple):
    p_inside: List['Port']
    p_outside: List['Port']
    n_inside: List['Node']
    n_outside: List['Node']
    links: List['Link']


def topology_to_nx_graph(topology: 'Topology', nodes: Optional[List['Node']] = None) -> nx.MultiGraph:
    """

    @param topology:
    @param nodes:
    @return:
    """
    graph = nx.MultiGraph()
    if nodes:
        node_ids = [n.id for n in nodes]
    else:
        node_ids = [n.id for n in topology.nodes()]

    graph.add_nodes_from(node_ids)

    link_pairs = [(l.n1.id, l.n2.id, {"id": l.id})
                  for l in topology.links()
                  if l.n1.id in graph and l.n2.id in graph]

    graph.add_edges_from(link_pairs)

    return graph


def connected_components(topology: 'Topology',
                         nodes: Optional[List['Node']] = None) -> List[List['Node']]:
    """

    @param topology:
    @param nodes:
    @return:
    """
    if nodes is not None and len(nodes) == 0:
        # otherwise networkx returns all components for graph
        # if want all nodes, then use nodes=None
        return []
    graph = topology_to_nx_graph(topology, nodes)

    components = nx.connected_components(graph)
    components = list(components)
    result = []
    for component in components:
        nodes = [topology.get_node_by_id(nid) for nid in component]
        result.append(nodes)

    return result


def boundary_links(topology: 'Topology', nodes: List['Node']) -> List['Link']:
    """

    @param topology:
    @param nodes:
    @return:
    """
    graph = topology_to_nx_graph(topology)
    node_ids = [n.id for n in nodes]

    edges = nx.edge_boundary(graph, node_ids, data=True)
    edge_ids = [data.get("id") for _, _, data in edges]
    links = [topology.get_link_by_id(lid) for lid in edge_ids]
    return links


def boundary_elements(topology: 'Topology', nodes: List['Node']) -> BoundaryData:
    """

    @param topology:
    @param nodes:
    @return:
    """
    links = boundary_links(topology, nodes)

    p_inside = []
    p_outside = []
    n_inside = []
    n_outside = []

    nodes = set(nodes)
    for link in links:
        if link.n1 in nodes:
            n_inside.append(link.n1)
            n_outside.append(link.n2)
            p_inside.append(link.p1)
            p_outside.append(link.p2)

        else:
            n_inside.append(link.n2)
            n_outside.append(link.n1)
            p_inside.append(link.p2)
            p_outside.append(link.p1)

    return BoundaryData(p_inside, p_outside, n_inside, n_outside, links)


def merge_nodes(topology: 'Topology', nodes: List['Node'],
                label: Optional[str] = None) -> 'Node':
    """

    @param topology:
    @param nodes:
    @param label:
    @return:
    """
    # returns the newly created merged node
    boundary_data = boundary_elements(topology, nodes)
    topology.remove_nodes_from(nodes)
    topology.remove_links_from(boundary_data.links)

    if not label:
        label = ""

    virtual_node = topology.create_node(DeviceType.VIRTUAL, label=label)

    for p_outside in boundary_data.p_outside:
        p_inside = virtual_node.create_port(PortType.LOGICAL)
        topology.create_link(p_inside, p_outside)

    return virtual_node


def split_link(topology: 'Topology', link: ['Link'],
               label: Optional[str] = None) -> 'Node':
    """

    @param topology:
    @param link:
    @param label:
    @return:
    """
    if not label:
        label = ""

    virtual_node = topology.create_node(DeviceType.VIRTUAL, label=label)

    p1 = virtual_node.create_port(PortType.LOGICAL)
    topology.create_link(link.p1, p1)
    p2 = virtual_node.create_port(PortType.LOGICAL)
    topology.create_link(link.p2, p2)

    topology.remove_link(link)

    return virtual_node


def explode_node(topology: 'Topology', node: 'Node') -> List['Link']:
    """

    @param topology:
    @param node:
    @return:
    """
    result = []
    peer_ports = node.peer_ports()
    topology.remove_node(node)

    pairs = [(x, y) for x in peer_ports for y in peer_ports
             if x != y]

    for p1, p2 in pairs:
        link = topology.create_link(p1, p2)
        result.append(link)

    return result


def links_contained_by_nodes(topology: 'Topology', nodes: List['Node']) -> List['Link']:
    """

    @param topology:
    @param nodes:
    @return:
    """
    nodes = set(nodes)
    result = []
    for link in topology.links():
        if link.n1 in nodes and link.n2 in nodes:
            result.append(link)

    return result


def wrap_node_ids(topology: 'Topology', nodes: List[NodeId]) -> List['Node']:
    """

    @param topology:
    @param nodes:
    @return:
    """
    return [topology.get_node_by_id(nid) for nid in nodes]


def force_layout(topology: 'Topology', scale: int = 500):
    """

    @param topology:
    @param scale:
    @return:
    """
    # note applies to global layout, but based on connectivity of provided topology
    try:
        import numpy
    except ImportError:
        logger.warning("Layout requires numpy to be installed")
        return
    graph = topology_to_nx_graph(topology)
    print(graph)
    center = [scale / 2, scale / 2]
    pos = nx.spring_layout(graph, center=center, scale=scale)
    for node_id, (x, y) in pos.items():
        node = topology.get_node_by_id(node_id)
        node.set("x", x)
        node.set("y", y)

    normalise_node_locations(topology)


def normalise_node_locations(topology: 'Topology') -> None:
    """

    @param topology:
    """
    x_min = min(n.get("x") for n in topology.nodes())
    y_min = min(n.get("y") for n in topology.nodes())

    x_offset = y_offset = 0
    if x_min < 0:
        x_offset = 1 - x_min
    if y_min < 0:
        y_offset = 1 - y_min

    if x_offset or y_offset:
        for node in topology.nodes():
            node.set("x", node.get("x") + x_offset)
            node.set("y", node.get("y") + y_offset)