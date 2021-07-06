import dataclasses
import logging
from functools import partial
from typing import Dict

import dacite

from autonetkit.network_model.base.exceptions import PortNotFound, LinkNotFound, NodeNotFound
from autonetkit.network_model.base.generics import NM
from autonetkit.network_model.base.network_model import NetworkModel
from autonetkit.network_model.base.topology import Topology
from autonetkit.network_model.base.topology_element import TopologyElement
from autonetkit.network_model.base.types import DeviceType, PortType, LinkId, NodeId, PortId

logger = logging.getLogger(__name__)


def node_hook(topology: Topology, key: NodeId):
    if key:
        try:
            node = topology.get_node_by_id(key)
        except NodeNotFound:
            node = topology._node_cls()
            topology._nodes[key] = node
        return node


def port_hook(topology: Topology, key: PortId):
    if key:
        try:
            port = topology.get_port_by_id(key)
        except PortNotFound:
            port = topology._port_cls()
            topology._ports[key] = port
        return port


def link_hook(topology: Topology, key: LinkId):
    if key:
        try:
            link = topology.get_link_by_id(key)
        except LinkNotFound:
            link = topology._link_cls()
            topology._links[key] = link
        return link


def copy_into_dataclass(source, target):
    # from https://stackoverflow.com/q/57962873
    for field in dataclasses.fields(source):
        attr = getattr(source, field.name)
        setattr(target, field.name, attr)


def restore_topology(model_constructor: 'NM', exported: Dict) -> NM:
    model: 'NetworkModel' = model_constructor()

    # node these are hard-coded for now
    # TODO: define these better with a schema etc inside the frozenset

    # get topologies
    for topology in model.topologies():
        topology_node_hook = partial(node_hook, topology)
        topology_port_hook = partial(port_hook, topology)
        topology_link_hook = partial(link_hook, topology)

        # TODO: see if want to support forward refs on Paths also

        topology_data = exported[topology.id]
        dacite_config = dacite.Config(check_types=False, type_hooks={
            topology._node_cls: topology_node_hook,
            topology._port_cls: topology_port_hook,
            topology._link_cls: topology_link_hook,
        })

        _restore_nodes(dacite_config, topology, topology_data)
        _restore_ports(dacite_config, topology, topology_data)
        _restore_links(dacite_config, topology, topology_data)

    # TODO: do for topology level properties

    # TODO: do for network model level properties

    # TODO: allow setting network model level properties? eg test2 on the CustomNetworkModel - if so need to export also

    return model


def _restore_links(dacite_config: dacite.Config, topology: Topology, topology_data: Dict) -> None:
    model = topology.network_model
    for link_id, link_data in topology_data["links"].items():
        p1 = topology.get_port_by_id(link_data["p1"])
        p2 = topology.get_port_by_id(link_data["p2"])

        link_cls = topology._link_cls
        annotations = get_field_values(link_cls, link_data)

        # and update with the key values
        annotations["id"] = link_id
        annotations["p1"] = p1
        annotations["p2"] = p2
        annotations["topology"] = topology

        # don't check types as edge case with generics
        new_link = dacite.from_dict(data_class=link_cls, data=annotations,
                                    config=dacite_config)

        try:
            link = topology.get_link_by_id(link_id)
        except LinkNotFound:
            topology._links[link_id] = new_link
            link = new_link
        else:
            copy_into_dataclass(new_link, link)

        model.used_link_ids.add(link_id)


def _restore_ports(dacite_config: dacite.Config, topology: Topology, topology_data: Dict) -> None:
    port_global_ints = {"slot"}

    model = topology.network_model
    for port_id, port_data in topology_data["ports"].items():
        # lookup node
        node = topology.get_node_by_id(port_data["node"])
        port_cls = topology._port_cls
        annotations = get_field_values(port_cls, port_data)

        # and update with the key values
        annotations["id"] = port_id
        annotations["node"] = node

        # don't check types as edge case with generics
        new_port = dacite.from_dict(data_class=port_cls, data=annotations,
                                    config=dacite_config)

        try:
            port = topology.get_port_by_id(port_id)
        except PortNotFound:
            topology._ports[port_id] = new_port
            port = new_port
        else:
            copy_into_dataclass(new_port, port)

        model.used_port_ids.add(port_id)

        # and update type

        # import global properties
        for key in model.port_global_keys:
            try:
                val = port_data[key]
            except KeyError:
                # Not set
                # TODO: see if should init to base value
                continue

            if val and key in port_global_ints:
                # TODO: note no slot for lo0 - as optional -> handle special case once move globals to types
                val = int(val)

            if key == "type":
                val = PortType[val]

            model.port_globals[port_id][key] = val


def _restore_nodes(dacite_config: dacite.Config, topology: Topology, topology_data: Dict) -> None:
    node_global_ints = {"asn", "x", "y"}

    model = topology.network_model
    for node_id, node_data in topology_data["nodes"].items():
        node_cls = topology._node_cls
        annotations = get_field_values(node_cls, node_data)

        # and update with the key values
        annotations["id"] = node_id
        annotations["topology"] = topology

        # don't check types as edge case with generics
        new_node = dacite.from_dict(data_class=node_cls, data=annotations,
                                    config=dacite_config)

        # if exists
        try:
            node = topology.get_node_by_id(node_id)
        except NodeNotFound:
            topology._nodes[node_id] = new_node
            node = new_node
        else:
            copy_into_dataclass(new_node, node)

        model.used_node_ids.add(node_id)

        # import global properties
        for key in model.node_global_keys:
            try:
                val = node_data[key]
            except KeyError:
                # Not set
                # TODO: see if should init to base value
                continue

            if key in node_global_ints:
                val = int(val)
            elif key == "type":
                val = DeviceType[val]

            model.node_globals[node_id][key] = val

        # now set the other values for that node

        # TODO: set remaining into the _data .set() .get()
        # TODO: don't do this if strict is set


def get_field_values(element: TopologyElement, element_data: Dict):
    # TODO: return as a namedtuple
    skip = {"topology", "id", "_data", "node"}
    fields = dataclasses.fields(element)

    init_data = {}

    for field in fields:
        key = field.name

        if key in skip:
            continue

        try:
            val = element_data[key]
        except KeyError:
            # not set
            pass
        else:
            init_data[key] = val

    return init_data
