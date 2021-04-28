import logging

from autonetkit.design.utils import filters
from autonetkit.design.utils.graph_utils import connected_components
from autonetkit.network_model.topology import Topology
from autonetkit.network_model.types import DeviceType

logger = logging.getLogger(__name__)


def check_layer2_conn(topology: Topology) -> bool:
    """

    @param topology:
    @return:
    """
    valid = True

    components = connected_components(topology)
    if len(components) > 1:
        logger.warning("Disconnected network: %s components", len(components))
        valid = False

    routers = filters.routers(topology)

    routers_present = len(routers) > 0

    if routers_present:
        # check that all hosts connect to a router
        hosts = filters.hosts(topology)
        for host in hosts:
            peers = host.peer_nodes()
            if not any(n.type == DeviceType.ROUTER for n in peers):
                logger.warning("Host %s is not connected to a router", host.label)
                valid = False

    return valid
