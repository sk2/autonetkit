import logging
from collections import defaultdict
from typing import Dict, Set

from autonetkit.network_model.base.exceptions import LinkNotFound, PortNotFound, NodeNotFound
from autonetkit.network_model.base.generics import NM
from autonetkit.network_model.base.link import Link
from autonetkit.network_model.base.node import Node
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.topology_element import TopologyElement
from autonetkit.network_model.base.types import DeviceType, PortType
from autonetkit.network_model.base.utils import get_annotations, is_optional, get_optional_value, get_forward_ref_value, \
    get_topology_constructors, is_forward_ref

logger = logging.getLogger(__name__)


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

        # print("topology", topology.id)
        topology_data = exported[topology.id]
        # print("data", topology_data)
        for node_id, node_data in topology_data["nodes"].items():
            # print(node_id, node_data)
            node_type = DeviceType[node_data["type"]]
            label = node_data["label"]

            node = topology.create_node(node_type, label, id=node_id, warn_if_id_in_use=False)

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

                model.node_globals[node_id][key] = val

            # now set the other values for that node

            # TODO: set remaining into the _data .set() .get()
            # TODO: don't do this if strict is set

            _map_annotations(forward_refs, node, node_data, topology_constructors)

        # basic ports
        for port_id, port_data in topology_data["ports"].items():
            # print(port_id, port_data)
            # lookup node
            node = topology.get_node_by_id(port_data["node"])
            port_type = PortType[port_data["type"]]
            label = port_data["label"]

            port = topology.create_port(node, port_type, label, id=port_id)

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

                model.node_globals[port_id][key] = val

            _map_annotations(forward_refs, port, port_data, topology_constructors)

        # basic links
        for link_id, link_data in topology_data["links"].items():
            print(link_data)
            p1 = topology.get_port_by_id(link_data["p1"])
            p2 = topology.get_port_by_id(link_data["p2"])
            # print(node_id, node_data)
            # node_type = DeviceType[node_data["type"]]
            # label = node_data["label"]

            link = topology.create_link(p1, p2, id=link_id, warn_if_id_in_use=False)

            print("created link", link_id)

            _map_annotations(forward_refs, link, link_data, topology_constructors)

            pass

        print("forward refs", forward_refs)
        for element, elem_data in forward_refs.items():
            for key, (constructor, val) in elem_data.items():

                print("fwd ref", key, constructor, type(constructor))

                if issubclass(constructor, Node):
                    try:
                        node = topology.get_node_by_id(val)
                    except NodeNotFound as exc:
                        logger.exception("Can't find node")

                elif issubclass(constructor, Port):
                    try:
                        port = topology.get_port_by_id(val)
                    except PortNotFound as exc:
                        logger.exception("Can't find port")
                    else:
                        setattr(element, key, val)



                elif issubclass(constructor, Link):
                    try:
                        link = topology.get_link_by_id(val)
                    except LinkNotFound as exc:
                        logger.exception("Can't find link")
                    else:
                        setattr(element, key, val)

                else:
                    # TODO: logging.warning
                    print("Unsupported forward reference", constructor)

    # TODO: do for topology level properties

    # TODO: do for network model level properties

    # TODO: allow setting network model level proeprties? eg test2 on the CustomNetworkModel - if so need to export also

    return model


def _map_annotations(forward_refs, element: TopologyElement, element_data: Dict, topology_constructors):
    for key, constructor in get_annotations(element).items():
        try:
            val = element_data[key]
        except KeyError:
            # node has no data for this value -> continue
            continue

        # TODO: also restore sequences and mappings

        # TODO: wrap this so don't fail all if incorrect type
        if is_optional(constructor):
            # get the other value
            optional_constructor = get_optional_value(constructor)

            if is_forward_ref(optional_constructor):
                # don't create, but get the value
                forward_ref_value = get_forward_ref_value(optional_constructor)
                fwd_constructor = get_forward_value_from_constructors(forward_ref_value, topology_constructors)
                if fwd_constructor and val is not None:
                    forward_refs[element][key] = (fwd_constructor, val)
            else:
                val = optional_constructor(val)
                setattr(element, key, val)
        else:
            if is_forward_ref(constructor):
                fwd_constructor = get_forward_value_from_constructors(constructor, topology_constructors)
                if fwd_constructor and val is not None:
                    forward_refs[element][key] = (fwd_constructor, val)
            else:
                val = constructor(val)
                setattr(element, key, val)


def get_forward_value_from_constructors(forward_ref_value, topology_constructors: Set[object]):
    for constructor in topology_constructors:
        if constructor.__name__ == forward_ref_value:
            return constructor
    return None
