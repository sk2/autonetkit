import itertools
from collections import defaultdict
from typing import Dict, List, Generic

from autonetkit.network_model.base.exceptions import TopologyNotFound
from autonetkit.network_model.base.generics import T
from autonetkit.network_model.base.topology import Topology
from autonetkit.network_model.base.topology_element import BaseTopology
from autonetkit.network_model.base.types import TopologyId, NodeId, PortId, LinkId, PathId
from autonetkit.network_model.base.utils import get_annotations


class NetworkModel(Generic[T]):
    t_base: Topology

    """

    """

    def __init__(self):
        self._topologies: Dict[TopologyId, T] = {}

        # create mandatory topologies
        # TODO refactor to be specific/custom then
        self.create_topology("input")
        self.create_topology("physical")

        self.node_globals: Dict[NodeId, Dict] = defaultdict(dict)
        self.port_globals: Dict[PortId, Dict] = defaultdict(dict)

        # TODO: deprecate these -> move to
        self.node_global_keys = frozenset(["type", "label", "asn", "x", "y", "target", "lo0_id"])
        self.port_global_keys = frozenset(["type", "label", "slot"])

        self.used_node_ids = set()
        self.used_link_ids = set()
        self.used_port_ids = set()
        self.used_path_ids = set()

        # TODO: enforce structure of t_ and then strip the t_ for naming
        # instantiate defined values
        # and store these topologies for the lookup accessor
        self._class_topologies = {}

        for key, cls in get_annotations(self).items():
            if issubclass(cls, Topology):
                topology = cls(self, key)
                setattr(self, key, topology)
                self._class_topologies[key] = topology


    @property
    def _node_ids(self):
        for x in itertools.count():
            candidate = f"n{x}"
            if candidate not in self.used_node_ids:
                self.used_node_ids.add(candidate)
                yield candidate

    @property
    def _link_ids(self):
        for x in itertools.count():
            candidate = f"l{x}"
            if candidate not in self.used_link_ids:
                self.used_link_ids.add(candidate)
                yield candidate

    @property
    def _port_ids(self):
        for x in itertools.count():
            candidate = f"p{x}"
            if candidate not in self.used_port_ids:
                self.used_port_ids.add(candidate)
                yield candidate

    @property
    def _path_ids(self):
        for x in itertools.count():
            candidate = f"pa{x}"
            if candidate not in self.used_path_ids:
                self.used_path_ids.add(candidate)
                yield candidate

    def get_topology(self, name) -> BaseTopology:
        """

        @param name:
        @return:
        """
        try:
            return self._class_topologies[name]
        except KeyError:
            try:
                return self._topologies[name]
            except KeyError:
                raise TopologyNotFound(name)

    def create_topology(self, name) -> T:
        """

        @param name:
        @return:
        """
        topology = Topology(self, name)
        self._topologies[name] = topology
        return topology

    def generate_node_id(self) -> NodeId:
        """

        @return:
        """
        return NodeId(next(self._node_ids))

    def generate_link_id(self) -> LinkId:
        """

        @return:
        """
        return LinkId(next(self._link_ids))

    def generate_port_id(self) -> PortId:
        """

        @return:
        """
        return PortId(next(self._port_ids))

    def generate_path_id(self) -> PathId:
        """

        @return:
        """
        return PathId(next(self._path_ids))

    def topologies(self) -> List[Topology]:
        result = list(self._topologies.values())
        result += list(self._class_topologies.values())
        return result

    def export(self) -> Dict:
        """

        @return:
        """
        result = {}
        # for name, topology in self._topologies.items():
        #     result[name] = topology.export()

        #TODO: rework this to export from the two topology dictionaries

        for topology in self.topologies():
            result[topology.id] = topology.export()

        return result
