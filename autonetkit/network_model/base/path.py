from typing import Dict, List, Generic

from autonetkit.network_model.base.generics import T, N, P
from autonetkit.network_model.base.topology_element import TopologyElement
from autonetkit.network_model.base.utils import initialise_annotation_defaults


class NodePath(TopologyElement, Generic[T, N, P]):
    """

    """

    def __init__(self, topology, id, nodes: List[N]):
        initialise_annotation_defaults(self)

        self.id = id
        self.topology = topology
        self.nodes: List[N] = nodes
        self._data: Dict = {}

    @property
    def local_data(self) -> Dict:
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

    def export(self) -> Dict:
        """

        @return:
        """
        data = self._data.copy()
        data["nodes"] = [n.id for n in self.nodes]
        return data


class PortPath(TopologyElement, Generic[T, N, P]):
    """

    """

    def __init__(self, topology, id, ports: List[P]):
        initialise_annotation_defaults(self)

        self.id = id
        self.topology = topology
        self.ports: List[P] = ports
        self._data = {}

    @property
    def local_data(self) -> Dict:
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

    def export(self) -> Dict:
        """

        @return:
        """
        data = self._data.copy()
        data["ports"] = [n.id for n in self.ports]
        return data
