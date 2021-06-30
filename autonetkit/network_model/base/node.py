from typing import Generic, Dict, List

from autonetkit.network_model.base.exceptions import PortNotFound
from autonetkit.network_model.base.generics import N, L, P, T
from autonetkit.network_model.base.types import NodeId, DeviceType, PortType
from autonetkit.network_model.base.utils import export_data, initialise_annotation_defaults


class Node(Generic[T, L, P]):
    test_inside: str = "testing"
    test333: int = 123
    """

    """

    def __init__(self, topology: T, id):
        initialise_annotation_defaults(self)

        self.topology: T = topology
        self.id: NodeId = id
        self._data: Dict = {}


    @property
    def local_data(self) -> Dict:
        """

        @return:
        """
        return self._data

    @property
    def global_data(self) -> Dict:
        """

        @return:
        """
        return self.topology.network_model.node_globals[self.id]

    def __repr__(self):
        return f"N {self.get('label')}"

    def ports(self) -> List[P]:
        """

        @return:
        """
        return self.topology.ports(node=self)

    def links(self) -> List[L]:
        """

        @return:
        """
        return self.topology.links(node=self)

    def create_port(self, type: PortType) -> P:
        """

        @param type:
        @return:
        """
        port = self.topology.create_port(self, type)
        return port

    def set(self, key, val) -> None:
        """

        @param key:
        @param val:
        """
        if key in self.topology.network_model.node_global_keys:
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
            if key in self.topology.network_model.node_global_keys:
                return self.global_data[key]
            else:
                return self._data[key]
        except KeyError:
            return default

    def gget(self, key, default=None):
        if key in self.topology.network_model.node_global_keys:
            try:
                return self.global_data[key]
            except KeyError:
                return default
        else:
            # TODO: make proper exception
            raise KeyError("Key is not global")

    def gset(self, key, val):
        if key in self.topology.network_model.node_global_keys:
            self.global_data[key] = val
        else:
            # TODO: make proper exception
            raise KeyError("Key is not global")

    def export(self) -> Dict:
        """

        @return:
        """

        skip = {"topology"}
        data = export_data(self, skip)

        return data

    def peer_nodes(self) -> List[N]:
        """

        @return:
        """
        result = []
        for link in self.links():
            other = link.other_node(self)
            result.append(other)

        return result

    def peer_ports(self) -> List[P]:
        """

        @return:
        """
        result = []
        for link in self.links():
            if link.n1 == self:
                result.append(link.p2)
            else:
                result.append(link.p1)

        return result

    def degree(self) -> int:
        """

        @return:
        """
        return len(self.links())

    def loopback_zero(self) -> P:
        """

        @return:
        """
        lo0_id = self.get("lo0_id")
        if lo0_id is None:
            raise PortNotFound("loopback_zero")
        else:
            return self.topology.get_port_by_id(lo0_id)

    @property
    def type(self) -> DeviceType:
        return self.global_data["type"]

    @type.setter
    def type(self, value):
        self.global_data["type"] = value

    @property
    def label(self) -> str:
        return self.global_data["label"]

    @label.setter
    def label(self, value):
        self.global_data["label"] = value

    @property
    def asn(self) -> int:
        return self.global_data["asn"]

    @asn.setter
    def asn(self, value):
        self.global_data["asn"] = value
