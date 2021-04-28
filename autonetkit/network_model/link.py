import typing

from autonetkit.network_model.exceptions import NodeNotFound
from autonetkit.network_model.types import LinkId

if typing.TYPE_CHECKING:
    from autonetkit.network_model.port import Port
    from autonetkit.network_model.node import Node
    from autonetkit.network_model.topology import Topology


class Link:
    """

    """

    def __init__(self, topology, id, p1: 'Port', p2: 'Port'):
        self.topology: Topology = topology
        self.id: LinkId = id
        self.p1: Port = p1
        self.p2: Port = p2
        self._data = {}

    @property
    def local_data(self) -> typing.Dict:
        """

        @return:
        """
        return self._data

    def __repr__(self):
        return f"L {self.p1}.{self.n1} {self.p1}.{self.n2}"

    def set(self, key, val) -> None:
        """

        @param key:  The key to set
        @param val:  The value to set
        """
        self._data[key] = val

    def get(self, key, default=None):
        """

        @param key: the key to get
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
        data["p1"] = self.p1.id
        data["p2"] = self.p2.id
        data["n1"] = self.p1.node.id
        data["n2"] = self.p2.node.id
        return data

    @property
    def n1(self) -> 'Node':
        """

        @return:
        """
        return self.p1.node

    @property
    def n2(self) -> 'Node':
        """

        @return:
        """
        return self.p2.node

    def other_node(self, node: 'Node') -> 'Node':
        """

        @param node:
        @return: the other node to the parameter
        """
        if self.n1 == node:
            return self.n2
        elif self.n2 == node:
            return self.n1
        else:
            raise NodeNotFound(node)
