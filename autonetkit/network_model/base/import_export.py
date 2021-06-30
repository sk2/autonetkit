from typing import Dict

from autonetkit.network_model.base.generics import NM
from autonetkit.network_model.base.types import DeviceType
from autonetkit.network_model.base.utils import get_annotations, is_optional, get_optional_value


def restore_topology(model_constructor: 'NM', exported: Dict) -> NM:
    model: 'NetworkModel' = model_constructor()

    # node these are hard-coded for now
    # TODO: define these better with a schema etc inside the frozenset
    node_global_ints = {"asn", "x", "y"}
    port_global_ints = {"slot"}

    # get topologies
    for topology in model.topologies():
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

            #TODO: set remaining into the _data .set() .get()
            #TODO: don't do this if strict is set

            for key, constructor in get_annotations(node).items():
                try:
                    val = node_data[key]
                except KeyError:
                    continue

                #TODO: wrap this so don't fail all if incorrect type
                if is_optional(constructor):
                    # get the other value
                    optional_constructor = get_optional_value(constructor)
                    print("optional", optional_constructor)
                    val = optional_constructor(val)
                    setattr(node, key, val)
                else:
                    val = constructor(val)
                    setattr(node, key, val)





    #TODO: do for ports

    # TODO: do for links

    # TODO: do for topology level properties

    #TODO: do for network model level properties

    #TODO: allow setting network model elvel proeprties? eg test2 on the CustomNetworkModel - if so need to export also



    return model