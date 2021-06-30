import typing
from typing import Dict

if typing.TYPE_CHECKING:
    pass


#TODO: see if should from future_import etc


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


def initialise_annotation_defaults(obj) -> None:
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
        print(type(result))
        if isinstance(result, typing.ForwardRef):
            args = typing.get_args(result)
            print("forward ref", args)
        return result
    else:
        raise TypeError