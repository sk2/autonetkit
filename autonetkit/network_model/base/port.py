from typing import Generic, Dict, List

from autonetkit.network_model.base.generics import N, L, P, T
from autonetkit.network_model.base.types import PortType, PortId
from autonetkit.network_model.base.utils import export_data


class Port(Generic[T, L, P]):
    some_port_test = 123
    """

    """

    def __init__(self, node: N, id):
        self._node: N = node
        self.id: PortId = id
        self._data = {}

    def __repr__(self):
        return f"P {self.get('label')}"

    @property
    def local_data(self) -> Dict:
        """

        @return:
        """
        return self._data

    @property
    def label(self) -> str:
        """

        @return:
        """
        return self.get("label")

    @property
    def type(self) -> PortType:
        """

        @return:
        """
        return self.get("type")

    @property
    def slot(self) -> int:
        """

        @return:
        """
        return self.get("slot")

    @property
    def global_data(self) -> Dict:
        """

        @return:
        """
        return self._node.topology.network_model.port_globals[self.id]

    @property
    def node(self) -> N:
        """

        @return:
        """
        return self._node

    def set(self, key, val) -> None:
        """

        @param key:
        @param val:
        """
        if key in self.node.topology.network_model.port_global_keys:
            self.global_data[key] = val
        else:
            self._data[key] = val

    def get(self, key, default=None):
        """

        @param key:
        @param default:
        @return:
        """
        try:
            if key in self.node.topology.network_model.port_global_keys:
                return self.global_data[key]
            else:
                return self._data[key]
        except KeyError:
            return default

    def export(self) -> Dict:
        """

        @return:
        """
        print("exporting port")
        skip = {"topology", "_node"}
        data = export_data(self, skip)

        data["node"] = self._node.id

        return data

    def links(self) -> List[L]:
        """

        @return:
        """
        result = [l for l in (self.node.links())
                  if l.p1 == self
                  or l.p2 == self]
        return result

    def peer_nodes(self, unique=True) -> List[N]:
        """

        @param unique:
        @return:
        """
        result = []
        for link in self.links():
            if link.p1 == self:
                result.append(link.n2)
            else:
                result.append(link.n1)

        if unique:
            result = list(set(result))

        return result

    def peer_ports(self, unique=True) -> List[P]:
        """

        @param unique:
        @return:
        """
        result = []
        for link in self.links():
            if link.p1 == self:
                result.append(link.p2)
            else:
                result.append(link.p1)

        if unique:
            result = list(set(result))

        return result

    def degree(self) -> int:
        """

        @return:
        """
        return len(self.links())

    @property
    def connected(self) -> bool:
        """

        @return:
        """
        return self.degree() > 0
