import typing

from autonetkit.network_model.exceptions import PortNotFound
from autonetkit.network_model.types import NodeId, DeviceType, PortType

if typing.TYPE_CHECKING:
    from autonetkit.network_model.topology import Topology
    from autonetkit.network_model.port import Port
    from autonetkit.network_model.link import Link


class Node:
    """

    """

    def __init__(self, topology: 'Topology', id):
        self.topology: Topology = topology
        self.id: NodeId = id
        self._data = {}

    @property
    def local_data(self) -> typing.Dict:
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
    def type(self) -> DeviceType:
        """

        @return:
        """
        return self.get("type")

    @property
    def global_data(self) -> typing.Dict:
        """

        @return:
        """
        return self.topology.network_model.node_globals[self.id]

    def __repr__(self):
        return f"N {self.get('label')}"

    def ports(self) -> typing.List['Port']:
        """

        @return:
        """
        return self.topology.ports(node=self)

    def links(self) -> typing.List['Link']:
        """

        @return:
        """
        return self.topology.links(node=self)

    def create_port(self, type: PortType) -> 'Port':
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

    def export(self) -> typing.Dict:
        """

        @return:
        """
        data = self.global_data.copy()
        data.update(self._data.copy())
        return data

    def peer_nodes(self) -> typing.List['Node']:
        """

        @return:
        """
        result = []
        for link in self.links():
            other = link.other_node(self)
            result.append(other)

        return result

    def peer_ports(self) -> typing.List['Port']:
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

    def loopback_zero(self) -> 'Port':
        """

        @return:
        """
        lo0_id = self.get("lo0_id")
        if lo0_id is None:
            raise PortNotFound("loopback_zero")
        else:
            return self.topology.get_port_by_id(lo0_id)
