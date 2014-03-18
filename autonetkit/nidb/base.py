import autonetkit.log as log

from autonetkit.nidb.interface import DmInterface
from autonetkit.nidb.edge import DmEdge
from autonetkit.nidb.node import DmNode
from autonetkit import ank_json

class DmBase(object):
    #TODO: inherit common methods from same base as overlay
    def __init__(self):
        #TODO: make optional for restore serialized file on init
        self._graph = None
        pass

    def __getstate__(self):
        return self._graph

    def __setstate__(self, state):
        self._graph = state

    def __repr__(self):
        return "nidb"

    # Model-level functions

    def save(self, timestamp = True, use_gzip = True):
        import os
        import gzip
        archive_dir = os.path.join("versions", "nidb")
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

        data = ank_json.ank_json_dumps(self._graph)
        if timestamp:
            json_file = "nidb_%s.json.gz" % self.timestamp
        else:
            json_file = "nidb.json"
        json_path = os.path.join(archive_dir, json_file)
        log.debug("Saving to %s" % json_path)
        if use_gzip:
            with gzip.open(json_path, "wb") as json_fh:
                json_fh.write(data)
        else:
            with open(json_path, "wb") as json_fh:
                json_fh.write(data)


    def interface(self, interface):
        return DmInterface(self,
                interface.node_id, interface.interface_id)

    def restore_latest(self, directory = None):
        import os
        import glob
        if not directory:
        #TODO: make directory loaded from config
            directory = os.path.join("versions", "nidb")

        glob_dir = os.path.join(directory, "*.json.gz")
        pickle_files = glob.glob(glob_dir)
        pickle_files = sorted(pickle_files)
        try:
            latest_file = pickle_files[-1]
        except IndexError:
            # No files loaded
            log.warning("No previous DeviceModel saved. Please compile new DeviceModel")
            return
        self.restore(latest_file)
        ank_json.rebind_nidb_interfaces(self)

    def restore(self, pickle_file):
        import gzip
        log.debug("Restoring %s" % pickle_file)
        with gzip.open(pickle_file, "r") as fh:
            #data = json.load(fh)
            data = fh.read()
            self._graph = ank_json.ank_json_loads(data)

        ank_json.rebind_nidb_interfaces(self)

    @property
    def name(self):
        return self.__repr__()

    def raw_graph(self):
        """Returns the underlying NetworkX graph"""
        return self._graph

    def copy_graphics(self, G_graphics):
        """Transfers graphics data from anm to nidb"""
        for node in self:
            node.add_stanza("graphics")
            graphics_node = G_graphics.node(node)
            node.graphics.x = graphics_node.x
            node.graphics.y = graphics_node.y
            node.graphics.device_type = graphics_node.device_type
            node.graphics.device_subtype = graphics_node.device_subtype
            node.device_type = graphics_node.device_type
            node.device_subtype = graphics_node.device_subtype

    def __len__(self):
        return len(self._graph)

    @property
    def data(self):
        from autonetkit.nidb.device_model import DmGraphData
        return DmGraphData(self)

    # Nodes

    def __iter__(self):
        return iter(DmNode(self, node)
                for node in self._graph)

    def node(self, key):
        """Returns node based on name
        This is currently O(N). Could use a lookup table"""
        try:
            if key.node_id in self._graph:
                return DmNode(self, key.node_id)
        except AttributeError:
            # doesn't have node_id, likely a label string, search on label
            for node in self:
                if str(node) == key:
                    return node
                elif node.id == key:
                    # label could be "a b" -> "a_b" (ie folder safe, etc)
                    #TODO: need to fix this discrepancy
                    return node
            print "Unable to find node", key, "in", self
            return None

    def update(self, nbunch, **kwargs):
        for node in nbunch:
            for (_, key), value in kwargs.items():
                node.category.set(key, value)

    def nodes(self, *args, **kwargs):
        result = self.__iter__()
        if len(args) or len(kwargs):
            result = self.filter(result, *args, **kwargs)
        return result

    def routers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be router"""

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_router()]

    def switches(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be switch"""

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_switch()]

    def servers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be server"""

        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_server()]

    def l3devices(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be server"""
        result = self.nodes(*args, **kwargs)
        return [r for r in result if r.is_l3device()]

    def filter(self, nbunch = None, *args, **kwargs):
        #TODO: also allow nbunch to be passed in to subfilter on...?
        """TODO: expand this to allow args also, ie to test if value evaluates to True"""
        # need to allow filter_func to access these args
        if not nbunch:
            nbunch = self.nodes()
        def filter_func(node):
            return (
                    all(getattr(node, key) for key in args) and
                    all(getattr(node, key) == val for key, val in kwargs.items())
                    )

        return (n for n in nbunch if filter_func(n))

    def add_nodes_from(self, nbunch, retain=None, **kwargs):
        if retain is None:
            retain = []
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        nbunch = list(nbunch)
        nodes_to_add = nbunch # retain for interface copying

        if len(retain):
            add_nodes = []
            for n in nbunch:
                data = dict( (key, n.get(key)) for key in retain)
                add_nodes.append( (n.node_id, data) )
            nbunch = add_nodes
        else:
            log.warning("Cannot add node ids directly to DeviceModel: must add overlay nodes")
        self._graph.add_nodes_from(nbunch, **kwargs)

        for node in nodes_to_add:
            #TODO: add an interface_retain for attributes also
            int_dict = {i.interface_id: {'type': i.type,
                'description': i.description,
                'layer': i.overlay_id} for i in node.interfaces()}
            int_dict = {i.interface_id: {'type': i.type,
                'description': i.description,
                } for i in node.interfaces()}
            self._graph.node[node.node_id]["_ports"] = int_dict

    # Edges

    def edges(self, nbunch = None, *args, **kwargs):
        # nbunch may be single node
        #TODO: Apply edge filters
        if nbunch:
            try:
                nbunch = nbunch.node_id
            except AttributeError:
                nbunch = (n.node_id for n in nbunch) # only store the id in overlay

        def filter_func(edge):
            return (
                    all(getattr(edge, key) for key in args) and
                    all(getattr(edge, key) == val for key, val in kwargs.items())
                    )

        #TODO: See if more efficient way to access underlying data structure rather than create overlay to throw away
        all_edges = iter(DmEdge(self, src, dst)
                for src, dst in self._graph.edges(nbunch)
                )
        return (edge for edge in all_edges if filter_func(edge))

    def edge(self, edge_to_find):
        """returns edge in this graph with same src and dst"""
        #TODO: check if this even needed - will be if searching nidb specifically
        # but that's so rare (that's a design stage if anywhere)
        src_id = edge_to_find.src
        dst_id = edge_to_find.dst
        for (src, dst) in self._graph.edges_iter(src_id):
            if dst == dst_id:
                return DmEdge(self._anm, self._overlay_id,
                    src, dst)

    def add_edge(self, src, dst, retain=None, **kwargs):
        if retain is None:
            retain = []
        self.add_edges_from([(src, dst)], retain, **kwargs)

    def add_edges_from(self, ebunch, retain=None, **kwargs):
        if retain is None:
            retain = []
        #TODO: need to retain interface references
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        edges_to_add = ebunch # retain for interface copying

        try:
            if len(retain):
                add_edges = []
                for e in ebunch:
                    data = dict( (key, e.get(key)) for key in retain)
                    add_edges.append( (e.src.node_id, e.dst.node_id, data) )
                ebunch = add_edges
            else:
                ebunch = [(e.src.node_id, e.dst.node_id) for e in ebunch]
        except AttributeError:
            ebunch = [(src.node_id, dst.node_id) for src, dst in ebunch]

        self._graph.add_edges_from(ebunch, **kwargs)
        for edge in edges_to_add:
            self._graph[edge.src.node_id][edge.dst.node_id]['_ports'] = edge.raw_interfaces
