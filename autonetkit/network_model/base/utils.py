from typing import Dict

import typing

from autonetkit.network_model.base.generics import NM
from autonetkit.network_model.base.types import DeviceType

if typing.TYPE_CHECKING:
    from autonetkit.network_model.base.network_model import NetworkModel


def export_data(cls, skip: set) -> Dict:
    # don't include the internal data dictionary
    skip.add("_data")

    try:
        data = cls.global_data.copy()
    except AttributeError:
        # no global data set, eg for link, path
        data = {}

    # TODO: deprecate this
    data.update(cls._data.copy())

    # Get any annotated fields
    for base in reversed(cls.__class__.__mro__):
        annotations = base.__dict__.get('__annotations__', {})
        for key, val in annotations.items():
            try:
                data[key] = getattr(cls, key)
            except AttributeError:
                # may not have been initialised
                pass

    for key, val in cls.__dict__.items():
        if key not in skip:
            data[key] = val

    return data


def import_data(cls, data):
    for base in reversed(cls.__class__.__mro__):
        annotations = base.__dict__.get('__annotations__', {})
        for key, type_to_cast in annotations.items():
            if key in data:
                # TODO: catch cast error
                val = type_to_cast(data[key])
                setattr(cls, key, val)


def get_annotations(cls) -> Dict:
    result = {}
    for base in reversed(cls.__class__.__mro__):
        annotations = base.__dict__.get('__annotations__', {})
        for key, val in annotations.items():
            result[key] = val
    return result


def initialise_annotation_defaults(cls) -> None:
    for key, constructor in get_annotations(cls).items():
        try:
            val = getattr(cls, key)
        except AttributeError:
            # not set, initialise
            setattr(cls, key, constructor())


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
                val = constructor(val)
                setattr(node, key, val)





    #TODO: do for ports

    # TODO: do for links

    # TODO: do for topology level properties

    #TODO: do for network model level properties

    #TODO: allow setting network model elvel proeprties? eg test2 on the CustomNetworkModel - if so need to export also



    return model
