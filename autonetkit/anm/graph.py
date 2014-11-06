import autonetkit.log as log
from autonetkit.ank_utils import unwrap_edges, unwrap_nodes
from autonetkit.anm.base import OverlayBase
from autonetkit.anm.edge import NmEdge
from autonetkit.anm.interface import NmPort
from autonetkit.anm.node import NmNode
import autonetkit


class NmGraph(OverlayBase):

    """API to interact with an overlay graph in ANM"""

    @property
    def anm(self):
        """Returns anm for this overlay

        >>> anm = autonetkit.topos.house()

        """

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

    def _record_overlay_dependencies(self, nbunch):
        # TODO: add this logic to anm so can call when instantiating overlays too
        # TODO: make this able to be disabled for performance
        g_deps = self.anm['_dependencies']
        overlays = {n.overlay_id for n in nbunch if isinstance(n, NmNode)}
        if len(overlays) and self._overlay_id not in g_deps:
            g_deps.add_node(self._overlay_id)
        for overlay_id in overlays:
            if overlay_id not in g_deps:
                g_deps.add_node(overlay_id)

            if g_deps.number_of_edges(self._overlay_id, overlay_id) == 0:
                edge = (overlay_id, self._overlay_id)
                g_deps.add_edges_from([edge])

    def add_nodes_from( self, nbunch, retain=None, update=False,
        **kwargs):
        """Update won't append data (which could clobber) if node exists"""
        nbunch = list(nbunch)  # listify in case consumed in try/except

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        self._record_overlay_dependencies(nbunch)

        if not update:
            # TODO: what is update used for?
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
                # TODO: should this just fall through instead to phy/anm label
                # function?
                node_data["label"] = str(node)  # use node id

        self._copy_interfaces(node_ids)

    def _copy_interfaces(self, nbunch):
        """Copies ports from one overlay to another"""

        nbunch = [n.node_id if isinstance(n, NmNode) else n
                  for n in nbunch]

        if self._overlay_id == "phy":
            # note: this will auto copy data from input if present - by default
            # TODO: provide an option to add_nodes to skip this
            # or would it be better to just provide a function in ank_utils to
            # wipe interfaces in the rare case it's needed?
            input_graph = self._anm.overlay_nx_graphs['input']
            for node_id in nbunch:
                if node_id not in input_graph:
                    log.debug("Not copying interfaces for %s: ",
                              "not in input graph %s" % node_id)
                    self._graph.node[node_id]['_ports'] = {
                        0: {'description': 'loopback', 'category': 'loopback'}}
                    continue

                try:
                    input_interfaces = input_graph.node[node_id]['_ports']
                except KeyError:
                    #Node not in input
                    # Just do base initialisation of loopback zero
                    self._graph.node[node_id]['_ports'] = {
                        0: {'description': 'loopback', 'category': 'loopback'}}
                else:
                    interface_data = {'description': None,
                                      'category': 'physical'}
                    # need to do dict() to copy, otherwise all point to same memory
                    # location -> clobber
                    # TODO: update this to also get subinterfaces?
                    # TODO: should description and category auto fall through?
                    data = dict((key, dict(interface_data)) for key in
                                input_interfaces)
                    ports = {}
                    for key, vals in input_interfaces.items():
                        port_data = {}
                        ports[key] = dict(vals)

                    # force 0 to be loopback
                    # TODO: could warn if already set
                    ports[0] = {
                        'description': 'loopback', 'category': 'loopback'}
                    self._graph.node[node_id]['_ports'] = ports
            return

        if self._overlay_id == "graphics":
            # TODO: remove once graphics removed
            return

        phy_graph = self._anm.overlay_nx_graphs['phy']
        for node_id in nbunch:
            try:
                phy_interfaces = phy_graph.node[node_id]['_ports']
            except KeyError:
                # Node not in phy (eg broadcast domain)
                # Just do base initialisation of loopback zero
                self._graph.node[node_id]['_ports'] = {
                    0: {'description': 'loopback', 'category': 'loopback'}}
            else:
                interface_data = {'description': None,
                                  'category': 'physical'}
                # need to do dict() to copy, otherwise all point to same memory
                # location -> clobber
                # TODO: update this to also get subinterfaces?
                # TODO: should description and category auto fall through?
                data = dict((key, dict(interface_data)) for key in
                            phy_interfaces)
                self._graph.node[node_id]['_ports'] = data

    def add_node(self, node, retain=None, **kwargs):
        """Adds node to overlay"""
        nbunch = [node]
        self.add_nodes_from(nbunch,
                            retain, **kwargs)
        #TODO: test what this code is meant to do
        try:
            node_id = node.id
        except AttributeError:
            node_id = node  # use the string node id
        return NmNode(self.anm, self._overlay_id, node_id)

    def allocate_input_interfaces(self):
        """allocates edges to interfaces"""
        # TODO: move this to ank utils? or extra step in the anm?
        if self._overlay_id != "input":
            log.debug("Tried to allocate interfaces to %s" % overlay_id)
            return

        if all(len(node['input'].raw_interfaces) > 0 for node in self) \
            and all(len(edge['input'].raw_interfaces) > 0 for edge in
                    self.edges()):
            log.debug("Input interfaces allocated")
            return  # interfaces allocated
        else:
            log.info('Automatically assigning input interfaces')

        # Initialise loopback zero on node
        for node in self:
            node.raw_interfaces = {0:
                                   {'description': 'loopback', 'category': 'loopback'}}

        ebunch = sorted(self.edges())
        for edge in ebunch:
            src = edge.src
            dst = edge.dst
            src_int_id = src._add_interface('%s to %s' % (src.label,
                                                          dst.label))
            dst_int_id = dst._add_interface('%s to %s' % (dst.label,
                                                          src.label))
            edge.raw_interfaces = {
                src.id: src_int_id,
                dst.id: dst_int_id}

    def number_of_edges(self, node_a, node_b):
        return self._graph.number_of_edges(node_a, node_b)

    def __delitem__(self, key):
        """Alias for remove_node. Allows
        del overlay[node]
        """
        # TODO: needs to support node types
        self.remove_node(key)

    def remove_nodes_from(self, nbunch):
        """Removes set of nodes from nbunch"""

        try:
            nbunch = unwrap_nodes(nbunch)
        except AttributeError:
            pass  # don't need to unwrap

        self._graph.remove_nodes_from(nbunch)

    def remove_node(self, node_id):
        """Removes a node from the overlay"""
        if isinstance(node_id, NmNode):
            node_id = node_id.node_id

        self._graph.remove_node(node_id)

    def add_edge(self, src, dst, retain=None, **kwargs):
        """Adds an edge to the overlay"""

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list
        retval = self.add_edges_from([(src, dst)], retain, **kwargs)
        return retval[0]

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

    def add_edges_from(self, ebunch, bidirectional=False, retain=None,
                       warn=True, **kwargs):
        """Add edges. Unlike NetworkX, can only add an edge if both
        src and dst in graph already.
        If they are not, then they will not be added (silently ignored)


        Retains interface mappings if they are present (this is why ANK
            stores the interface reference on the edges, as it simplifies
            cross-layer access, as well as split, aggregate, etc retaining the
            interface bindings)_

        Bidirectional will add edge in both directions. Useful if going
        from an undirected graph to a
        directed, eg G_in to G_bgp
        #TODO: explain "retain" and ["retain"] logic

        if user wants to add from another overlay, first go g_x.edges()
        then add from the result

        allow (src, dst, ekey), (src, dst, ekey, data) for the ank utils
        """

        if not retain:
            retain = []
        try:
            retain.lower()
            retain = [retain]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        # TODO: this needs to support parallel links

        all_edges = []
        for in_edge in ebunch:
            """Edge could be one of:
            - NmEdge
            - (NmNode, NmNode)
            - (NmPort, NmPort)
            - (NmNode, NmPort)
            - (NmPort, NmNode)
            - (string, string)
            """
            # This is less efficient than nx add_edges_from, but cleaner logic
            # TODO: could put the interface data into retain?
            data = {'_ports': {}}  # to retain
            ekey = None  # default is None (nx auto-allocates next int)

            # convert input to a NmEdge
            src = dst = None
            if isinstance(in_edge, NmEdge):
                edge = in_edge  # simple case
                ekey = edge.ekey  # explictly set ekey
                src = edge.src.node_id
                dst = edge.dst.node_id

                # and copy retain data
                data = dict((key, edge.get(key)) for key in retain)
                ports = {k: v for k, v in edge.raw_interfaces.items()
                         if k in self._graph}  # only if exists in this overlay
                # TODO: debug log if skipping a binding?
                data['_ports'] = ports

                # this is the only case where copy across data
                # but want to copy attributes for all cases

            elif len(in_edge) == 2:
                in_a, in_b = in_edge[0], in_edge[1]

                if isinstance(in_a, NmNode) and isinstance(in_b, NmNode):
                    src = in_a.node_id
                    dst = in_b.node_id

                elif isinstance(in_a, NmPort) and isinstance(in_b, NmPort):
                    src = in_a.node.node_id
                    dst = in_b.node.node_id
                    ports = {}
                    if src in self:
                        ports[src] = in_a.interface_id
                    if dst in self:
                        ports[dst] = in_b.interface_id
                    data['_ports'] = ports

                elif isinstance(in_a, NmNode) and isinstance(in_b, NmPort):
                    src = in_a.node_id
                    dst = in_b.node.node_id
                    ports = {}
                    if dst in self:
                        ports[dst] = in_b.interface_id
                    data['_ports'] = ports

                elif isinstance(in_a, NmPort) and isinstance(in_b, NmNode):
                    src = in_a.node.node_id
                    dst = in_b.node_id
                    ports = {}
                    if src in self:
                        ports[src] = in_a.interface_id
                    data['_ports'] = ports

                elif in_a in self and in_b in self:
                    src = in_a
                    dst = in_b

            elif len(in_edge) == 3:
                # (src, dst, ekey) format
                # or (src, dst, data) format
                in_a, in_b, in_c = in_edge[0], in_edge[1], in_edge[2]
                if in_a in self and in_b in self:
                    src = in_a
                    dst = in_b
                    # TODO: document the following logic
                    if self.is_multigraph() and not isinstance(in_c, dict):
                        ekey = in_c
                    else:
                        data = in_c

            elif len(in_edge) == 4:
                # (src, dst, ekey, data) format
                in_a, in_b = in_edge[0], in_edge[1]
                if in_a in self and in_b in self:
                    src = in_a
                    dst = in_b
                    ekey = in_edge[2]
                    data = in_edge[3]

            # TODO: if edge not set at this point, give error/warn

            # TODO: add check that edge.src and edge.dst exist
            if (src is None or dst is None) and warn:
                log.warning("Unsupported edge %s" % str(in_edge))
            if not(src in self and dst in self):
                if warn:
                    self.log.debug("Not adding edge %s, src/dst not in overlay"
                                   % str(in_edge))
                continue

            # TODO: warn if not multigraph and edge already exists - don't
            # add/clobber
            data.update(**kwargs)

            edges_to_add = []
            if self.is_multigraph():
                edges_to_add.append((src, dst, ekey, dict(data)))
                if bidirectional:
                    edges_to_add.append((dst, src, ekey, dict(data)))
            else:
                edges_to_add.append((src, dst, dict(data)))
                if bidirectional:
                    edges_to_add.append((dst, src, dict(data)))


            #TODO: warn if not multigraph

            self._graph.add_edges_from(edges_to_add)
            all_edges += edges_to_add

        if self.is_multigraph():
            return [NmEdge(self.anm, self._overlay_id, src, dst, ekey)
            for src, dst, ekey, _ in all_edges]
        else:
            return [NmEdge(self.anm, self._overlay_id, src, dst)
            for src, dst, _ in all_edges]

    def update(self, nbunch=None, **kwargs):
        """Sets property defined in kwargs to all nodes in nbunch"""

        if nbunch is None:
            nbunch = self.nodes()

        if nbunch in self:
            nbunch = [nbunch]  # single node in the list for iteration

        # if the node is in the underlying networkx graph, then map to an
        # overlay node
        nbunch = [self.node(n) if n in self._graph else n for n in nbunch]
        for node in nbunch:
            for (key, value) in kwargs.items():
                node.set(key, value)

    def subgraph(self, nbunch, name=None):
        """"""

        nbunch = (n.node_id for n in nbunch)  # only store the id in overlay
        from autonetkit.anm.subgraph import OverlaySubgraph
        return OverlaySubgraph(self._anm, self._overlay_id,
                               self._graph.subgraph(nbunch), name)
