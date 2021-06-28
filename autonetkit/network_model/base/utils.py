from typing import Dict


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
    print("import")

    for base in reversed(cls.__class__.__mro__):
        annotations = base.__dict__.get('__annotations__', {})
        for key, type_to_cast in annotations.items():
            if key in data:
                print("set key", key, data[key], type_to_cast)
                #TODO: catch cast error
                val = type_to_cast(data[key])
                setattr(cls, key, val)


