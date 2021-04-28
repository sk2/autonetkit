import itertools

from autonetkit.design.utils import filters
from autonetkit.design.utils.general import move_to_average_peer_locations
from autonetkit.design.utils.graph_utils import connected_components, merge_nodes, split_link, explode_node
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.types import DeviceType, LAYER3_DEVICES


def build_l2(network_model: NetworkModel):
    """

    @param network_model:
    """
    # TODO: check if should be called l2 or broadcast domains
    # TODO: later extend to support managed switches also
    t_phy = network_model.get_topology("physical")
    t_l2 = network_model.create_topology("layer2")

    # TODO: later can filter out hubs, optical gear, etc if included from l1 topology
    t_l2.add_nodes_from(t_phy.nodes())
    t_l2.add_links_from(t_phy.links())

    # merge switches
    switches = filters.switches(t_l2)
    components = connected_components(t_l2, switches)

    labels = (f"bc_{x}" for x in itertools.count())

    for component_nodes in components:
        label = next(labels)
        merged = merge_nodes(t_l2, component_nodes, label=label)
        move_to_average_peer_locations(merged)

        merged.set("type", DeviceType.BROADCAST_DOMAIN)

    # split router ptp links
    ptp_links = [l for l in t_l2.links()
                 if l.n1.type in LAYER3_DEVICES
                 and l.n2.type in LAYER3_DEVICES]

    for link in ptp_links:
        label = next(labels)
        split = split_link(t_l2, link, label)
        move_to_average_peer_locations(split)
        split.set("type", DeviceType.BROADCAST_DOMAIN)


def build_l2_conn(network_model):
    """

    @param network_model:
    """
    t_l2 = network_model.get_topology("layer2")
    t_l2_conn = network_model.create_topology("layer2_conn")

    t_l2_conn.add_nodes_from(t_l2.nodes())
    t_l2_conn.add_links_from(t_l2.links())
    bc_nodes = filters.broadcast_domains(t_l2_conn)

    for node in bc_nodes:
        explode_node(t_l2_conn, node)
