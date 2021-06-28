import typing
from typing import Dict


def export_data(self, skip) -> Dict:
    try:
        data = self.global_data.copy()
    except AttributeError:
        # no global data set, eg for link, path
        data = {}

    # TODO: deprecate this
    data.update(self._data.copy())

    # super hints
    for base in self.__class__.__bases__:
        type_hints = typing.get_type_hints(base)
        for key in type_hints:
            data[key] = getattr(self, key)

    type_hints = typing.get_type_hints(self)
    for key in type_hints:
        data[key] = getattr(self, key)

    for key, val in self.__dict__.items():
        if key not in skip:
            data[key] = val

    return data