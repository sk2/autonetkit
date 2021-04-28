import logging
import typing
from collections import defaultdict
from typing import List, Dict

from autonetkit.network_model.exceptions import NodeNotFound, LinkNotFound, PortNotFound, PortIdInUse, LinkIdInUse, \
    NodeIdInUse, PathIdInUse, NumericNodeId
from autonetkit.network_model.link import Link
from autonetkit.network_model.node import Node
from autonetkit.network_model.path import NodePath, PortPath
from autonetkit.network_model.port import Port
from autonetkit.network_model.types import DeviceType, NodeId, TopologyId, LinkId, PortId, PortType, PathId

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from autonetkit.network_model.network_model import NetworkModel


class Topology:
    """

    """

    def __init__(self, network_model, id: TopologyId):
        self.id: TopologyId = id
        self.network_model: NetworkModel = network_model
        self._nodes: Dict[NodeId: Node] = {}
        self._links: Dict[LinkId: Link] = {}
        self._ports: Dict[PortId, Port] = {}
        self._node_paths: Dict[PathId, NodePath] = {}
        self._port_paths: Dict[PathId, PortPath] = {}

        self._cache_ports_for_node: Dict[NodeId, List[Port]] = defaultdict(list)
        self._cache_links_for_node: Dict[NodeId, List[Link]] = defaultdict(list)

        self._data = {}

    def create_node(self, type: DeviceType, label: typing.Optional[str] = None,
                    id: typing.Optional[NodeId] = None) -> 'Node':
        """

        @param type:
        @param label:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_node_ids:
                raise NodeIdInUse(id)
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

    def _create_node(self, node_id):
        node = Node(self, node_id)
        self._nodes[node_id] = node
        return node

    def create_port(self, node: 'Node', type: PortType, label: typing.Optional[str] = None,
                    id: typing.Optional[PortId] = None) -> 'Port':
        """

        @param node:
        @param type:
        @param label:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_port_ids:
                raise PortIdInUse(id)
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

    def _create_port(self, node, port_id):
        port = Port(node, port_id)
        self._cache_ports_for_node[port.node.id].append(port)
        self._ports[port_id] = port
        return port

    def create_link(self, p1: 'Port', p2: 'Port',
                    id: typing.Optional[LinkId] = None) -> 'Link':
        """

        @param p1:
        @param p2:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_link_ids:
                raise LinkIdInUse(id)
            else:
                self.network_model.used_link_ids.add(id)
                link_id = id
        else:
            link_id = self.network_model.generate_link_id()
        link = self._create_link(link_id, p1, p2)

        return link

    def _create_link(self, link_id, p1, p2):
        # TODO: warn if port types are not the same
        link = Link(self, link_id, p1, p2)
        self._links[link_id] = link
        self._cache_links_for_node[link.n1.id].append(link)
        self._cache_links_for_node[link.n2.id].append(link)
        return link

    def create_node_path(self, nodes: List[Node], id=None) -> NodePath:
        """

        @param nodes:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_path_ids:
                raise PathIdInUse(id)
            else:
                self.network_model.used_path_ids.add(id)
                path_id = id
        else:
            path_id = self.network_model.generate_path_id()
        path = NodePath(self, path_id, nodes)
        self._node_paths[path_id] = path
        return path

    def create_port_path(self, ports: List[Port], id=None) -> PortPath:
        """

        @param ports:
        @param id:
        @return:
        """
        if id is not None:
            if id in self.network_model.used_path_ids:
                raise PathIdInUse(id)
            else:
                self.network_model.used_path_ids.add(id)
                path_id = id
        else:
            path_id = self.network_model.generate_path_id()
        path = PortPath(self, path_id, ports)

        self._port_paths[path_id] = path
        return path

    def add_nodes_from(self, nodes: List['Node'], with_ports: bool = True,
                       ports: typing.Optional[typing.Iterable['Port']] = None):
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

    def add_links_from(self, links: List["Link"], raise_if_port_not_found=False):
        """

        @param links:
        @param raise_if_port_not_found:
        """
        for link in links:
            try:
                p1 = self.get_port_by_id(link.p1.id)
                p2 = self.get_port_by_id(link.p2.id)
            except PortNotFound:
                if raise_if_port_not_found:
                    raise
                else:
                    continue

            self._create_link(link.id, p1, p2)

    def remove_nodes_from(self, nodes: List['Node']) -> None:
        """

        @param nodes:
        """
        for node in nodes:
            self.remove_node(node)

    def remove_links_from(self, links: List['Link']) -> None:
        """

        @param links:
        """
        for link in links:
            self.remove_link(link)

    def remove_node(self, node: 'Node') -> None:
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

    def remove_link(self, link: 'Link') -> None:
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

    def remove_port(self, port: 'Port') -> None:
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

    def remove_node_path(self, path: 'NodePath') -> None:
        """

        @param path:
        """
        try:
            del self._node_paths[path.id]
        except KeyError:
            pass  # already removed

    def remove_port_path(self, path: 'PortPath') -> None:
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

    def nodes(self) -> typing.List['Node']:
        """

        @return:
        """
        return list(self._nodes.values())

    def ports(self, node: typing.Optional['Node'] = None) -> typing.List['Port']:
        """

        @param node:
        @return:
        """
        if node:
            return self._cache_ports_for_node[node.id]
        else:
            return list(self._ports.values())

    def links(self, node: typing.Optional['Node'] = None) -> typing.List['Link']:
        """

        @param node:
        @return:
        """
        if node:
            return self._cache_links_for_node[node.id]
        else:
            return list(self._links.values())

    def node_paths(self) -> typing.List['NodePath']:
        """

        @return:
        """
        return list(self._node_paths.values())

    def port_paths(self) -> typing.List['PortPath']:
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

    def get_node_by_id(self, nid: NodeId) -> 'Node':
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
                raise NumericNodeId(message)

            raise NodeNotFound(nid)

    def get_link_by_id(self, lid: LinkId) -> 'Link':
        """

        @param lid:
        @return:
        """
        try:
            return self._links[lid]
        except KeyError:
            raise LinkNotFound(lid)

    def get_port_by_id(self, pid: PortId) -> 'Port':
        """

        @param pid:
        @return:
        """
        try:
            return self._ports[pid]
        except KeyError:
            raise PortNotFound(pid)
