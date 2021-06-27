import logging
import typing
from collections import defaultdict
from typing import List, Dict

import autonetkit.network_model.base.exceptions as exceptions
from autonetkit.network_model.base.generics import N, L, P, NP, PP
from autonetkit.network_model.base.link import Link
from autonetkit.network_model.base.node import Node
from autonetkit.network_model.base.path import NodePath, PortPath
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.types import DeviceType, NodeId, TopologyId, LinkId, PortId, PortType, PathId

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from autonetkit.network_model.base.network_model import NetworkModel


class Topology(typing.Generic[N, L, P]):
    _node_cls = Node
    _link_cls = Link
    _port_cls = Port

    """

    """

    def __init__(self, network_model, id: TopologyId):
        self.id: TopologyId = id
        self.network_model: NetworkModel = network_model
        self._nodes: Dict[NodeId: N] = {}
        self._links: Dict[LinkId: L] = {}
        self._ports: Dict[PortId, P] = {}
        self._node_paths: Dict[PathId, NP] = {}
        self._port_paths: Dict[PathId, PP] = {}

        self._cache_ports_for_node: Dict[NodeId, List[P]] = defaultdict(list)
        self._cache_links_for_node: Dict[NodeId, List[L]] = defaultdict(list)

        self._data = {}

    def create_node(self, type: DeviceType, label: typing.Optional[str] = None,
                    id: typing.Optional[NodeId] = None) -> N:
        """

        @param type:
        @param label:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_node_ids:
                raise exceptions.NodeIdInUse(id)
            else:
                self.network_model.used_node_ids.add(id)
                node_id = id
        else:
            node_id = self.network_model.generate_node_id()

        node = self._create_node(node_id)
        node.set("type", type)
        if label:
            node.set("label", label)

        return node

    def _create_node(self, node_id) -> N:
        node = self._node_cls(self, node_id)
        self._nodes[node_id] = node
        return node

    def create_port(self, node: N, type: PortType, label: typing.Optional[str] = None,
                    id: typing.Optional[PortId] = None) -> P:
        """

        @param node:
        @param type:
        @param label:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_port_ids:
                raise exceptions.PortIdInUse(id)
            else:
                self.network_model.used_port_ids.add(id)
                port_id = id
        else:
            port_id = self.network_model.generate_port_id()
        port = self._create_port(node, port_id)
        port.set("type", type)
        if label:
            port.set("label", label)

        return port

    def _create_port(self, node: N, port_id: PortId):
        port = self._port_cls(node, port_id)
        self._cache_ports_for_node[port.node.id].append(port)
        self._ports[port_id] = port
        return port

    def create_link(self, p1: P, p2: P,
                    id: typing.Optional[LinkId] = None) -> L:
        """

        @param p1:
        @param p2:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_link_ids:
                raise exceptions.LinkIdInUse(id)
            else:
                self.network_model.used_link_ids.add(id)
                link_id = id
        else:
            link_id = self.network_model.generate_link_id()
        link = self._create_link(link_id, p1, p2)

        return link

    def _create_link(self, link_id, p1: P, p2: P) -> L:
        # TODO: warn if port types are not the same
        link = self._link_cls(self, link_id, p1, p2)
        self._links[link_id] = link
        self._cache_links_for_node[link.n1.id].append(link)
        self._cache_links_for_node[link.n2.id].append(link)
        return link

    def create_node_path(self, nodes: List[N], id=None, cls=NodePath) -> NP:
        """

        @param nodes:
        @param id:
        @return:
        """
        # TODO: allow specifying the class type
        if id is not None:
            if id in self.network_model.used_path_ids:
                raise exceptions.PathIdInUse(id)
            else:
                self.network_model.used_path_ids.add(id)
                path_id = id
        else:
            path_id = self.network_model.generate_path_id()
        path = cls(self, path_id, nodes)
        self._node_paths[path_id] = path
        return path

    def create_port_path(self, ports: List[P], id=None, cls=PortPath) -> PP:
        """

        @param ports:
        @param id:
        @return:
        """
        # TODO: allow specifying the class type
        if id is not None:
            if id in self.network_model.used_path_ids:
                raise exceptions.PathIdInUse(id)
            else:
                self.network_model.used_path_ids.add(id)
                path_id = id
        else:
            path_id = self.network_model.generate_path_id()
        path = cls(self, path_id, ports)

        self._port_paths[path_id] = path
        return path

    def add_nodes_from(self, nodes: List[N], with_ports: bool = True,
                       ports: typing.Optional[typing.Iterable[P]] = None):
        """

        @param nodes:
        @param with_ports:
        @param ports:
        """
        if ports:
            ports = set(ports)

        for original_node in nodes:
            node_id = original_node.id
            node = self._create_node(node_id)

            ports_to_copy = []
            if ports:
                ports_to_copy = set(node.ports()).intersection(ports)

            elif with_ports:
                ports_to_copy = original_node.ports()

            for port in ports_to_copy:
                self._create_port(node, port.id)

    def add_links_from(self, links: List[L], raise_if_port_not_found=False):
        """

        @param links:
        @param raise_if_port_not_found:
        """
        for link in links:
            try:
                p1 = self.get_port_by_id(link.p1.id)
                p2 = self.get_port_by_id(link.p2.id)
            except exceptions.PortNotFound:
                if raise_if_port_not_found:
                    raise
                else:
                    continue

            self._create_link(link.id, p1, p2)

    def remove_nodes_from(self, nodes: List[N]) -> None:
        """

        @param nodes:
        """
        for node in nodes:
            self.remove_node(node)

    def remove_links_from(self, links: List[L]) -> None:
        """

        @param links:
        """
        for link in links:
            self.remove_link(link)

    def remove_node(self, node: N) -> None:
        """

        @param node:
        """
        links = list(node.links())
        for link in links:
            self.remove_link(link)

        ports = list(node.ports())
        for port in ports:
            self.remove_port(port)

        try:
            del self._nodes[node.id]
        except KeyError:
            pass  # already removed

        try:
            del self._cache_ports_for_node[node.id]
            del self._cache_links_for_node[node.id]
        except KeyError:
            pass  # already removed

    def remove_link(self, link: L) -> None:
        """

        @param link:
        """
        # TODO: also allow to remove ports too?
        try:
            del self._links[link.id]
        except KeyError:
            pass  # already removed

        try:
            self._cache_links_for_node[link.n1.id].remove(link)
        except ValueError:
            pass  # already removed

        try:
            self._cache_links_for_node[link.n2.id].remove(link)
        except ValueError:
            pass  # already removed

    def remove_port(self, port: P) -> None:
        """

        @param port:
        """
        links = list(port.links())
        for link in links:
            # TODO: check this is correctly capturing the nodes/links
            self.remove_link(link)

        try:
            del self._ports[port.id]
        except KeyError:
            pass  # already removed

        try:
            self._cache_ports_for_node[port.node.id].remove(port)
        except ValueError:
            pass  # already removed

    def remove_node_path(self, path: NP) -> None:
        """

        @param path:
        """
        try:
            del self._node_paths[path.id]
        except KeyError:
            pass  # already removed

    def remove_port_path(self, path: PP) -> None:
        """

        @param path:
        """
        try:
            del self._port_paths[path.id]
        except KeyError:
            pass  # already removed

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

    def nodes(self) -> typing.List[N]:
        """

        @return:
        """
        return list(self._nodes.values())

    def ports(self, node: typing.Optional[N] = None) -> typing.List[P]:
        """

        @param node:
        @return:
        """
        if node:
            return self._cache_ports_for_node[node.id]
        else:
            return list(self._ports.values())

    def links(self, node: typing.Optional[N] = None) -> typing.List[L]:
        """

        @param node:
        @return:
        """
        if node:
            return self._cache_links_for_node[node.id]
        else:
            return list(self._links.values())

    def node_paths(self) -> typing.List[NP]:
        """

        @return:
        """
        return list(self._node_paths.values())

    def port_paths(self) -> typing.List[PP]:
        """

        @return:
        """
        return list(self._port_paths.values())

    def export(self) -> Dict:
        """

        @return:
        """
        result = {
            "nodes": {},
            "links": {},
            "ports": {},
            "node_paths": {},
            "port_paths": {}
        }

        for node_id, node in self._nodes.items():
            result["nodes"][node_id] = node.export()

        for link_id, link in self._links.items():
            result["links"][link_id] = link.export()

        for port_id, port in self._ports.items():
            result["ports"][port_id] = port.export()

        for path_id, path in self._node_paths.items():
            result["node_paths"][path_id] = path.export()

        for path_id, path in self._port_paths.items():
            result["port_paths"][path_id] = path.export()

        return result

    def get_node_by_id(self, nid: NodeId) -> N:
        """

        @param nid:
        @return:
        """
        try:
            return self._nodes[nid]
        except KeyError:
            if isinstance(nid, int):
                # may be from networkx
                message = f"Attempting to search for node by numeric id, cast to a string {nid}"
                raise exceptions.NumericNodeId(message)

            raise exceptions.NodeNotFound(nid)

    def get_link_by_id(self, lid: LinkId) -> L:
        """

        @param lid:
        @return:
        """
        try:
            return self._links[lid]
        except KeyError:
            raise exceptions.LinkNotFound(lid)

    def get_port_by_id(self, pid: PortId) -> P:
        """

        @param pid:
        @return:
        """
        try:
            return self._ports[pid]
        except KeyError:
            raise exceptions.PortNotFound(pid)
