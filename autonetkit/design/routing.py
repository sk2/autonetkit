from autonetkit.design.utils import filters
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.topology import Topology
from autonetkit.network_model.types import DeviceType


def _build_igp_base(network_model: NetworkModel, topology: Topology):
    t_l2_conn = network_model.get_topology("layer2_conn")
    routers = filters.routers(t_l2_conn)
    topology.add_nodes_from(routers)
    links = [l for l in t_l2_conn.links()
             if l.n1.type == l.n2.type == DeviceType.ROUTER
             and l.n1.get("asn") == l.n2.get("asn")]
    topology.add_links_from(links)
    # remove the zero degree routers -> no IGP to configure
    single_routers = [n for n in topology.nodes() if n.degree() == 0]
    topology.remove_nodes_from(single_routers)


def build_ospf(network_model: NetworkModel):
    """

    @param network_model:
    """
    t_ospf = network_model.create_topology("ospf")
    t_in = network_model.get_topology("input")
    _build_igp_base(network_model, t_ospf)
    for node in t_ospf.nodes():
        input_node = t_in.get_node_by_id(node.id)
        # TODO: allow specifying the OSPF area on input topology
        node.set("area", input_node.get("ospf_area"))
        node_area = node.get("area")
        for port in filters.physical_ports(node):
            port.set("area", node_area)


def build_isis(network_model: NetworkModel):
    """

    @param network_model:
    """
    t_isis = network_model.create_topology("isis")
    _build_igp_base(network_model, t_isis)


def build_ibgp(network_model: NetworkModel):
    """

    @param network_model:
    """
    t_ibgp = network_model.create_topology("ibgp")
    t_l2_conn = network_model.get_topology("layer2_conn")
    routers = filters.routers(t_l2_conn)
    t_ibgp.add_nodes_from(routers)
    pairs = [(s, t)
             for s in t_ibgp.nodes()
             for t in t_ibgp.nodes()
             if s.get("asn") == t.get("asn")
             if s != t]

    # get loopback

    for n1, n2 in pairs:
        p1 = n1.loopback_zero()
        p2 = n2.loopback_zero()
        t_ibgp.create_link(p1, p2)


def build_ebgp(network_model: NetworkModel):
    """

    @param network_model:
    """
    t_ebgp = network_model.create_topology("ebgp")
    t_l2_conn = network_model.get_topology("layer2_conn")
    routers = filters.routers(t_l2_conn)
    t_ebgp.add_nodes_from(routers)

    ebgp_links = [l for l in t_l2_conn.links()
                  if l.n1.get("asn") != l.n2.get("asn")]
    t_ebgp.add_links_from(ebgp_links)
