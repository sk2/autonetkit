import dataclasses
import typing
from typing import Dict

if typing.TYPE_CHECKING:
    from autonetkit.network_model.base.topology import Topology


# TODO: see if should from future_import etc


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
    fields = dataclasses.fields(cls)
    for field in fields:
        key = field.name
        if key in skip:
            continue

        try:
            data[key] = getattr(cls, key)
        except AttributeError:
            #TODO: see if can still reach here with
            # may not have been initialised
            pass

    # for key, val in cls.__dict__.items():
    #     if key not in skip:
    #         data[key] = val

    return data


def get_annotations(cls) -> Dict:
    result = {}
    for base in reversed(cls.__class__.__mro__):
        annotations = base.__dict__.get('__annotations__', {})
        for key, val in annotations.items():
            result[key] = val
    return result


def initialise_annotation_defaults(obj) -> None:
    return
    for key, constructor in get_annotations(obj).items():
        try:
            val = getattr(obj, key)
        except AttributeError:
            # handle Optional/Unions
            initialise_value(obj, constructor, key)


def initialise_value(obj, constructor, key):
    if is_optional(constructor):
        setattr(obj, key, None)
    else:
        if is_forward_ref(constructor):
            # Don't initialise this value
            pass
        else:
            setattr(obj, key, constructor())


def is_optional(constructor):
    if typing.get_origin(constructor) == typing.Union:
        args = typing.get_args(constructor)
        is_optional = type(None) in args
    else:
        is_optional = False
    return is_optional


def get_optional_value(constructor):

    if typing.get_origin(constructor) == typing.Union:
        args = typing.get_args(constructor)
        args = set(args)
        # remove the default of None
        args.remove(type(None))
        # return the remaining (non None) value
        result = args.pop()
        return result
    else:
        raise TypeError


def get_topology_constructors(topology: 'Topology') -> Dict:
    # returns list of all element constructors
    result = set()
    base_classes = list(reversed(topology.__class__.__mro__))
    for base in base_classes:
        # TODO: refactor this technique - it's a little hacky as will try for non-topology classes like Generic, Object etc
        try:
            result.add(base._node_cls)
        except AttributeError:
            pass

        try:
            result.add(base._link_cls)
        except AttributeError:
            pass

        try:
            result.add(base._port_cls)
        except AttributeError:
            pass

    # map to dict keyed by name for easy lookup later
    return {x.__name__: x for x in result}


def get_forward_ref_value(forward_ref: typing.ForwardRef) -> str:
    return forward_ref.__forward_arg__


def is_forward_ref(constructor):
    if isinstance(constructor, typing.ForwardRef):
        return True

    # TODO: rename function for this logic - if an alias
    if isinstance(constructor, str):
        return True

        # #TODO: see if better method to get ref value than string cast
        # res: typing.ForwardRef = result
        # print("name", res.__forward_arg__)
        # # constructor = types.new_class(name)
        # # print("got", constructor)
        #
        # # globalns = sys.modules[constructor.__module__].__dict__.copy()
        # # globalns.setdefault(constructor.__name__, constructor)
        # # return result._evaluate(globalns=globalns, localns=None)
        # test: typing.ForwardRef = result
        # print("val", result.__dict__)
        # args = typing.get_args(result)
        # print("forward ref", args, dir(args))
