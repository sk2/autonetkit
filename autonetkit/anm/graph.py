import autonetkit.log as log
from autonetkit.ank_utils import unwrap_edges, unwrap_nodes
from autonetkit.anm.base import OverlayBase
from autonetkit.anm.edge import NmEdge
from autonetkit.anm.interface import NmInterface
from autonetkit.anm.node import NmNode


class NmGraph(OverlayBase):

    """API to interact with an overlay graph in ANM"""

    @property
    def anm(self):
        """Returns anm for this overlay"""

        return self._anm

    @property
    def _graph(self):
        """Access underlying graph for this NmNode"""

        return self._anm.overlay_nx_graphs[self._overlay_id]

    def _replace_graph(self, graph):
        """"""

        self._anm.overlay_nx_graphs[self._overlay_id] = graph

    # these work similar to their nx counterparts: just need to strip the
    # node_id

    def add_nodes_from(
        self,
        nbunch,
        retain=None,
        update=False,
        **kwargs
    ):
        """Update won't append data (which could clobber) if node exists"""
        nbunch = list(nbunch)  # listify in case consumed in try/except

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        if not update:

# filter out existing nodes

            nbunch = (n for n in nbunch if n not in self._graph)

        nbunch = list(nbunch)
        node_ids = list(nbunch)  # before appending retain data

        if len(retain):
            add_nodes = []
            for node in nbunch:
                data = dict((key, node.get(key)) for key in retain)
                add_nodes.append((node.node_id, data))
            nbunch = add_nodes
        else:
            try:
                # only store the id in overlay
                nbunch = [n.node_id for n in nbunch]
            except AttributeError:
                pass  # use nbunch directly as the node IDs

        self._graph.add_nodes_from(nbunch, **kwargs)
        for node in self._graph.nodes():
            node_data = self._graph.node[node]
            if "label" not in node_data:
                node_data["label"] = str(node)  # use node id

        self._init_interfaces(node_ids)

    def add_node(
        self,
        node,
        retain=None,
        **kwargs
    ):
        """Adds node to overlay"""

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        try:
            node_id = node.id
        except AttributeError:
            node_id = node  # use the string node id

        data = {}
        if len(retain):
            data = dict((key, node.get(key)) for key in retain)
            kwargs.update(data)  # also use the retained data
        self._graph.add_node(node_id, kwargs)
        self._init_interfaces([node_id])

    def _init_interfaces(self, nbunch=None):
        """Initialises interfaces"""
        # TODO: this needs a major refactor!

        # store the original bunch to check if going input->phy
        if nbunch is not None:
            nbunch = list(nbunch)  # listify generators

        original_nbunch = {}

        if nbunch is None:
            nbunch = [n for n in self._graph.nodes()]

        try:
            previous = list(nbunch)
            nbunch = list(unwrap_nodes(nbunch))
        except AttributeError:
            pass  # don't need to unwrap
        else:
            # record a dict of the new nbunch to the original
            for index, element in enumerate(nbunch):
                previous_element = previous[index]
                if previous_element is not None:
                    original_nbunch[element] = previous[index]

        phy_graph = self._anm.overlay_nx_graphs['phy']

        initialised_nodes = []
        for node in nbunch:
            try:
                phy_interfaces = phy_graph.node[node]['_interfaces']
                interface_data = {'description': None,
                                  'type': 'physical'}

                # need to do dict() to copy, otherwise all point to same memory
                # location -> clobber

                data = dict((key, dict(interface_data)) for key in
                            phy_interfaces)
                self._graph.node[node]['_interfaces'] = data
            except KeyError:
                # TODO: split this off into seperate function
                # test if adding from input graph
                # Note: this has to be done on a node-by-node basis
                # as ANK allows adding nodes from multiple graphs at once
                # TODO: warn if adding from multiple overlays at onc
                if self._overlay_id == "phy" and len(original_nbunch):
                        # see if adding from input->phy,
                        # overlay nodes were provided as input
                        original_node = original_nbunch[node]
                        if original_node.overlay_id == "input":
                            # are doing input->phy
                            # copy the
                            original_interfaces = original_node.get(
                                "_interfaces")
                            if original_interfaces is not None:
                                # Initialise with the keys
                                int_data = {k: {"description": v.get("description"), "type": v.get("type")}
                                            for k, v in original_interfaces.items()}
                                self._graph.node[node][
                                    '_interfaces'] = int_data

                else:
                    # no counterpart in physical graph, initialise
                    # Can't do node log becaue node doesn't exist yet
                    self._graph.node[node]['_interfaces'] = \
                        {0: {'description': 'loopback', 'type': 'loopback'}}
                    initialised_nodes.append(node)

        if len(initialised_nodes):
            initialised_nodes = [NmNode(self.anm, self._overlay_id, n) for n in initialised_nodes]
            initialised_nodes = sorted([str(n) for n in initialised_nodes])
            self.log.debug("Initialised interfaces for %s" % ", ".join(initialised_nodes))

    def allocate_interfaces(self):
        """allocates edges to interfaces"""

        if self._overlay_id in ('input', 'phy'):
            if all(len(node['input']._interfaces) > 0 for node in self) \
                and all(len(edge['input']._interfaces) > 0 for edge in
                        self.edges()):
                input_interfaces_allocated = True
            else:
                log.info('Automatically assigning input interfaces')
                input_interfaces_allocated = False

        if self._overlay_id == 'input':

            # only return if allocated here

            if input_interfaces_allocated:
                return   # already allocated

        # int_counter = (n for n in itertools.count() if n not in

        if self._overlay_id == 'phy':

            # check if nodes added

            nodes = list(self)
            edges = list(self.edges())
            if len(nodes) and len(edges):

                # allocate called once physical graph populated

                if input_interfaces_allocated:
                    for node in self:
                        input_interfaces = node['input']._interfaces
                        if len(input_interfaces):
                            node._interfaces = input_interfaces

                    for edge in self.edges():
                        edge._interfaces = edge['input']._interfaces
                        input_interfaces = edge['input']._interfaces
                        if len(input_interfaces):
                            edge._interfaces = input_interfaces
                    return

        self._init_interfaces()

        ebunch = sorted(self.edges())

        for edge in ebunch:
            src = edge.src
            dst = edge.dst
            dst = edge.dst
            src_int_id = src._add_interface('%s to %s' % (src.label,
                                                          dst.label))
            dst_int_id = dst._add_interface('%s to %s' % (dst.label,
                                                          src.label))
            edge._interfaces = {}
            edge._interfaces[src.id] = src_int_id
            edge._interfaces[dst.id] = dst_int_id

    def __delitem__(self, key):
        """Alias for remove_node. Allows
        >>> del overlay[node]
        """

        self.remove_node(key)

    def remove_node(self, node):
        """Removes a node from the overlay"""

        try:
            node_id = node.node_id
        except AttributeError:
            node_id = node
        self._graph.remove_node(node_id)

    def add_edge(
        self,
        src,
        dst,
        retain=None,
        **kwargs
    ):
        """Adds an edge to the overlay"""

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list
        self.add_edges_from([(src, dst)], retain, **kwargs)

    def remove_edges_from(self, ebunch):
        """Removes set of edges from ebunch"""

        try:
            ebunch = unwrap_edges(ebunch)
        except AttributeError:
            pass  # don't need to unwrap
        self._graph.remove_edges_from(ebunch)

    def add_edges(self, *args, **kwargs):
        """Adds a set of edges. Alias for add_edges_from"""

        self.add_edges_from(args, kwargs)

    def add_edges_from(
        self,
        ebunch,
        bidirectional=False,
        retain=None,
        **kwargs
    ):
        """Add edges. Unlike NetworkX, can only add an edge if both
        src and dst in graph already.
        If they are not, then they will not be added (silently ignored)

        Bidirectional will add edge in both directions. Useful if going
        from an undirected graph to a
        directed, eg G_in to G_bgp
        """

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        retain.append('_interfaces')
        try:
            if len(retain):
                add_edges = []
                for edge in ebunch:
                    data = dict((key, edge.get(key)) for key in retain)
                    add_edges.append((edge.src.node_id,
                                      edge.dst.node_id, data))
                ebunch = add_edges
            else:
                ebunch = [(e.src.node_id, e.dst.node_id, {}) for e in
                          ebunch]
        except AttributeError:
            ebunch_out = []
            for (src, dst) in ebunch:

                # TODO: check this works across nodes, etc

                if isinstance(src, NmInterface) \
                    and isinstance(dst, NmInterface):
                    _interfaces = {src.node_id: src.interface_id,
                                   dst.node_id: dst.interface_id}
                    ebunch_out.append((src.node_id, dst.node_id,
                                       {'_interfaces': _interfaces}))
                else:
                    try:
                        src_id = src.node_id
                    except AttributeError:
                        src_id = src  # use directly
                    try:
                        dst_id = dst.node_id
                    except AttributeError:
                        dst_id = dst  # use directly
                    ebunch_out.append((src_id, dst_id, {'_interfaces': {}}))

            ebunch = ebunch_out

        ebunch = [(src, dst, data) for (src, dst, data) in ebunch
                  if src in self._graph and dst in self._graph]
        if bidirectional:
            ebunch += [(dst, src, data) for (src, dst, data) in ebunch
                       if src in self._graph and dst in self._graph]

        self._graph.add_edges_from(ebunch, **kwargs)

    def update(self, nbunch=None, **kwargs):
        """Sets property defined in kwargs to all nodes in nbunch"""

        if nbunch is None:
            nbunch = self.nodes()

        if nbunch in self:
            nbunch = [nbunch]  # single node in the list for iteration

        # if the node is in the underlying networkx graph, then map to an overlay node
        nbunch = [self.node(n) if n in self._graph else n for n in nbunch]
        for node in nbunch:
            for (key, value) in kwargs.items():
                node.set(key, value)

    def update_edges(self, ebunch=None, **kwargs):
        """Sets property defined in kwargs to all edges in ebunch"""
        # TODO: also allow (src_id, dst_id) and single overlay edge

        if not ebunch:
            ebunch = self.edges()
        for edge in ebunch:
            for (key, value) in kwargs.items():
                edge.set(key, value)

    def subgraph(self, nbunch, name=None):
        """"""

        nbunch = (n.node_id for n in nbunch)  # only store the id in overlay
        from overlay_subgraph import OverlaySubgraph
        return OverlaySubgraph(self._anm, self._overlay_id,
                               self._graph.subgraph(nbunch), name)
