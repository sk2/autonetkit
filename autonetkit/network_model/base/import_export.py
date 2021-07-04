import dataclasses
import logging
from collections import defaultdict
from typing import Dict

import dacite

from autonetkit.network_model.base.exceptions import LinkNotFound, PortNotFound, NodeNotFound
from autonetkit.network_model.base.generics import NM
from autonetkit.network_model.base.link import Link
from autonetkit.network_model.base.network_model import NetworkModel
from autonetkit.network_model.base.node import Node
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.topology_element import TopologyElement
from autonetkit.network_model.base.types import DeviceType, PortType
from autonetkit.network_model.base.utils import get_topology_constructors

logger = logging.getLogger(__name__)


def update_forward_refs(element: TopologyElement, global_fwd_refs: Dict, local_fwd_refs: Dict) -> None:
    for key, val in local_fwd_refs.items():
        global_fwd_refs[element][key] = val


def restore_topology(model_constructor: 'NM', exported: Dict) -> NM:
    model: 'NetworkModel' = model_constructor()

    # node these are hard-coded for now
    # TODO: define these better with a schema etc inside the frozenset
    node_global_ints = {"asn", "x", "y"}
    port_global_ints = {"slot"}

    # get topologies
    for topology in model.topologies():

        topology_constructors = get_topology_constructors(topology)

        # TODO: see if want to support forward refs on Paths also
        forward_refs = defaultdict(dict)

        topology_data = exported[topology.id]
        for node_id, node_data in topology_data["nodes"].items():
            node_cls = topology._node_cls
            annotations, local_fwd_refs = _map_annotations(node_cls, node_data, topology_constructors)

            # and update with the key values
            annotations["id"] = node_id
            annotations["topology"] = topology

            # don't check types as edge case with generics
            node = dacite.from_dict(data_class=node_cls, data=annotations,
                                    config=dacite.Config(check_types=False))

            topology._nodes[node_id] = node
            model.used_node_ids.add(node_id)

            update_forward_refs(node, forward_refs, local_fwd_refs)

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

        # basic ports
        for port_id, port_data in topology_data["ports"].items():
            # lookup node
            node = topology.get_node_by_id(port_data["node"])
            port_cls = topology._port_cls
            annotations, local_fwd_refs = _map_annotations(port_cls, port_data, topology_constructors)

            # and update with the key values
            annotations["id"] = port_id
            annotations["node"] = node

            # don't check types as edge case with generics
            port = dacite.from_dict(data_class=port_cls, data=annotations,
                                    config=dacite.Config(check_types=False))

            topology._ports[port_id] = port
            model.used_port_ids.add(port_id)

            update_forward_refs(port, forward_refs, local_fwd_refs)

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

                model.node_globals[port_id][key] = val

        for link_id, link_data in topology_data["links"].items():
            p1 = topology.get_port_by_id(link_data["p1"])
            p2 = topology.get_port_by_id(link_data["p2"])

            link_cls = topology._link_cls
            annotations, local_fwd_refs = _map_annotations(link_cls, link_data, topology_constructors)

            # and update with the key values
            annotations["id"] = link_id
            annotations["p1"] = p1
            annotations["p2"] = p2

            # don't check types as edge case with generics
            link = dacite.from_dict(data_class=link_cls, data=annotations,
                                    config=dacite.Config(check_types=False))

            topology._links[link_id] = link
            model.used_link_ids.add(link_id)

            update_forward_refs(link, forward_refs, local_fwd_refs)

        for element, elem_data in forward_refs.items():
            for key, (constructor, val) in elem_data.items():

                if issubclass(constructor, Node):
                    try:
                        node = topology.get_node_by_id(val)
                    except NodeNotFound:
                        logger.exception("Can't find node")
                    else:
                        setattr(element, key, node)

                elif issubclass(constructor, Port):
                    try:
                        port = topology.get_port_by_id(val)
                    except PortNotFound:
                        logger.exception("Can't find port")
                    else:
                        setattr(element, key, port)



                elif issubclass(constructor, Link):
                    try:
                        link = topology.get_link_by_id(val)
                    except LinkNotFound:
                        logger.exception("Can't find link")
                    else:
                        setattr(element, key, link)

                else:
                    # TODO: logging.warning
                    print("Unsupported forward reference", constructor)

    # TODO: do for topology level properties

    # TODO: do for network model level properties

    # TODO: allow setting network model level proeprties? eg test2 on the CustomNetworkModel - if so need to export also

    return model


def _map_annotations(element: TopologyElement, element_data: Dict, topology_constructors: Dict):
    forward_refs = {}
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
            if field.type in topology_constructors and val is not None:
                constructor = topology_constructors[field.type]
                forward_refs[key] = (constructor, val)
            else:
                init_data[key] = val

    return init_data, forward_refs
