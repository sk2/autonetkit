import logging
from collections import Counter

from autonetkit.design.utils import filters
from autonetkit.network_model.exceptions import PortNotFound
from autonetkit.network_model.topology import Topology
from autonetkit.network_model.types import LAYER3_DEVICES

logger = logging.getLogger(__name__)


def validate(topology: Topology) -> bool:
    """
    TODO: can also check no two hosts directly connected, and only routers cross ASNs


    """
    valid = True
    if not labels_unique(topology):
        valid = False

    if not physical_ports_have_slot(topology):
        valid = False

    if not l3_nodes_have_loopback(topology):
        valid = False

    return valid


def physical_ports_have_slot(topology) -> bool:
    """

    @param topology:
    @return:
    """
    valid = True
    for node in topology.nodes():
        for port in filters.physical_ports(node):
            if port.slot is None:
                logger.warning("No slot allocated for %s on %s", port.label, node.label)
                valid = False

    return valid


def l3_nodes_have_loopback(topology) -> bool:
    """

    @param topology:
    @return:
    """
    valid = True
    layer3_nodes = [n for n in topology.nodes()
                    if n.type in LAYER3_DEVICES]
    for node in layer3_nodes:
        try:
            _ = node.loopback_zero()
        except PortNotFound:
            logger.warning("Loopback zero not set for %s", node.label)
            valid = False

    return valid


def labels_unique(topology) -> bool:
    """

    @param topology:
    @return:
    """
    valid = True
    label_counter = Counter()
    for node in topology.nodes():
        label_counter[node.label] += 1
    for label, count in label_counter.items():
        if count > 1:
            logger.warning("Label %s is present %s times", label, count)
            valid = False
    return valid
