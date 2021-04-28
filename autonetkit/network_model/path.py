import typing

if typing.TYPE_CHECKING:
    from autonetkit.network_model.port import Port
    from autonetkit.network_model.node import Node


class NodePath:
    """

    """

    def __init__(self, topology, id, nodes: typing.List['Node']):
        self.id = id
        self.topology = topology
        self.nodes: typing.List['Node'] = nodes
        self._data = {}

    @property
    def local_data(self) -> typing.Dict:
        """

        @return:
        """
        return self._data

    def __repr__(self):
        return f"P {[n.id for n in self.nodes]}"

    def set(self, key, val) -> None:
        """

        @param key:
        @param val:
        """
        self._data[key] = val

    def get(self, key, default=None):
        """

        @param key:
        @param default:
        @return:
        """
        try:
            return self._data[key]
        except KeyError:
            return default

    def export(self) -> typing.Dict:
        """

        @return:
        """
        data = self._data.copy()
        data["nodes"] = [n.id for n in self.nodes]
        return data


class PortPath:
    """

    """

    def __init__(self, topology, id, ports: typing.List['Port']):
        self.id = id
        self.topology = topology
        self.ports: typing.List['Port'] = ports
        self._data = {}

    @property
    def local_data(self) -> typing.Dict:
        """

        @return:
        """
        return self._data

    def __repr__(self):
        return f"P {[n.id for n in self.ports]}"

    def set(self, key, val) -> None:
        """

        @param key:
        @param val:
        """
        self._data[key] = val

    def get(self, key, default=None):
        """

        @param key:
        @param default:
        @return:
        """
        try:
            return self._data[key]
        except KeyError:
            return default

    def export(self) -> typing.Dict:
        """

        @return:
        """
        data = self._data.copy()
        data["ports"] = [n.id for n in self.ports]
        return data
