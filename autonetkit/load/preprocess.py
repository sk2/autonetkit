import itertools
from collections import defaultdict

from autonetkit.design.utils import filters
from autonetkit.load.model import StructuredTopology
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.types import PortType, NodeId, LinkId, PortId, DeviceType


def process_structured_topology(structure_topology: StructuredTopology) -> NetworkModel:
    """

    @param structure_topology:
    @return:
    """
    network_model = NetworkModel()

    t_in = network_model.get_topology("input")
    for node in structure_topology.nodes:
        for port in node.ports:
            if port.type == PortType.PHYSICAL:
                port.label = f"eth{port.slot}"
            if port.loopback_zero:
                port.label = "lo0"

    node_ids = {n.id for n in structure_topology.nodes}
    link_ids = {n.id for n in structure_topology.nodes}
    port_ids = {n.id for n in structure_topology.nodes}

    node_ids_gen = (NodeId(f"n{x}") for x in itertools.count()
                    if x not in node_ids)
    link_ids_gen = (LinkId(f"l{x}") for x in itertools.count()
                    if x not in link_ids)
    port_ids_gen = (PortId(f"p{x}") for x in itertools.count()
                    if x not in port_ids)

    for node in structure_topology.nodes:
        if node.id is None:
            node.id = next(node_ids_gen)
        for port in node.ports:
            if port.id is None:
                port.id = next(port_ids_gen)

    for link in structure_topology.links:
        if link.id is None:
            link.id = next(link_ids_gen)

    apply_defaults(structure_topology)
    vals_to_map = ["x", "y", "asn", "target"]
    for node in structure_topology.nodes:
        t_node = t_in.create_node(node.type, node.label, id=node.id)
        ndict = node.dict()
        for key in vals_to_map:
            t_node.set(key, ndict.get(key))

        # copy in data values
        for key, val in node.data.items():
            t_node.set(key, val)

        for port in node.ports:
            t_port = t_in.create_port(t_node, port.type, port.label, id=port.id)
            t_port.set("slot", port.slot)

            # copy in data values
            for key, val in port.data.items():
                t_port.set(key, val)

            if port.loopback_zero:
                t_node.set("lo0_id", port.id)

    # build map for fast lookup
    nodes_by_label = {}
    ports_by_node_slot = defaultdict(dict)
    for node in t_in.nodes():
        nodes_by_label[node.label] = node
        for port in filters.physical_ports(node):
            ports_by_node_slot[node.id][port.slot] = port

    for link in structure_topology.links:
        n1 = nodes_by_label[link.n1]
        n2 = nodes_by_label[link.n2]
        p1 = ports_by_node_slot[n1.id][link.p1]
        p2 = ports_by_node_slot[n2.id][link.p2]

        t_link = t_in.create_link(p1, p2, id=link.id)
        # copy in data values
        for key, val in link.data.items():
            t_link.set(key, val)

    return network_model


def apply_defaults(topology: StructuredTopology):
    """

    @param topology:
    """
    # TODO: allow passing config to apply
    DEFAULT_ASN = 1
    DEFAULT_OSPF_AREA = 0
    DEFAULT_TARGET = {
        DeviceType.ROUTER: "quagga",
        DeviceType.HOST: "linux",
        DeviceType.SWITCH: "mock_switch",
    }

    for node in topology.nodes:
        device_type = node.type
        if node.asn is None:
            node.asn = DEFAULT_ASN

        if node.target is None:
            node.target = DEFAULT_TARGET[device_type]

        if device_type == DeviceType.ROUTER:
            if node.data.get("ospf_area") is None:
                node.data["ospf_area"] = DEFAULT_OSPF_AREA
