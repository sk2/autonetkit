from dataclasses import dataclass
from typing import Generic, Dict

from autonetkit.network_model.base.exceptions import NodeNotFound
from autonetkit.network_model.base.generics import N, P, T
from autonetkit.network_model.base.topology_element import TopologyElement
from autonetkit.network_model.base.types import LinkId
from autonetkit.network_model.base.utils import export_data, initialise_annotation_defaults


@dataclass
class Link(TopologyElement, Generic[T, N, P]):
    topology: T = None
    id: LinkId = None
    p1: P = None
    p2: P = None

    abc: str = None
    link_basic: float = 20
    """

    """

    def __eq__(self, other):
        return self.id == other.id

    @property
    def local_data(self) -> Dict:
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

    def export(self) -> Dict:
        """

        @return:
        """
        skip = {"topology", "p1", "p2", "n1", "n2"}
        data = export_data(self, skip)

        #TODO: check if need to update with local data too
        # data = self._data.copy()
        data["p1"] = self.p1.id
        data["p2"] = self.p2.id
        data["n1"] = self.p1.node.id
        data["n2"] = self.p2.node.id

        return data

    @property
    def n1(self) -> N:
        """

        @return:
        """
        return self.p1.node

    @property
    def n2(self) -> N:
        """

        @return:
        """
        return self.p2.node

    def other_node(self, node: N) -> N:
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
