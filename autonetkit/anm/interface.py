import logging

import autonetkit.log as log
from autonetkit.log import CustomAdapter
from autonetkit.anm.ank_element import AnkElement


class NmPort(AnkElement):

    def __init__(self, anm, overlay_id, node_id, interface_id):
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'interface_id', interface_id)
        #logger = logging.getLogger("ANK")
        #logstring = "Interface: %s" % str(self)
        #logger = CustomAdapter(logger, {'item': logstring})
        logger = log
        object.__setattr__(self, 'log', logger)
        self.init_logging("port")


    def __key(self):
        """Note: key doesn't include overlay_id to allow fast cross-layer comparisons"""

        # based on http://stackoverflow.com/q/2909106

        return (self.interface_id, self.node_id)

    def __hash__(self):
        """"""

        return hash(self.__key())


    def __deepcopy__(self, memo):
        #TODO: workaround - need to fix
       # from http://stackoverflow.com/questions/1500718/what-is-the-right-way-to-override-the-copy-deepcopy-operations-on-an-object-in-p
       pass


    def __repr__(self):
        description = self.id or self.description
        return '%s.%s' % (description, self.node)

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __nonzero__(self):

        # TODO: work out why description and category being set/copied to each
        # overlay

        try:
            interface = self._interface
        except KeyError:
            return False

        return len(interface) > 0  # if interface data set

    def __lt__(self, other):

        # TODO: check how is comparing the node

        return (self.node, self.interface_id) < (other.node,
                                                 other.interface_id)


    @property
    def id(self):
        """Returns  id of node, falls-through to phy if not set on this overlay

        """
        #TODO: make generic function for fall-through properties stored on the anm
        key = "id"
        if key in self._interface:
                return self._interface.get(key)
        else:
            if self.overlay_id == "input":
                return  # Don't fall upwards from input -> phy as may not exist
            if self.overlay_id == "phy":
                return  # Can't fall from phy -> phy (loop)

            # try from phy

            if not self.node['phy']:
                # node not in phy
                return

            try:
                #return self.anm.overlay_nx_graphs['phy'].node[self.node_id]['asn']
                return self['phy'].id
            except KeyError:
                return # can't get from this overlay or phy -> not found

    @property
    def is_bound(self):
        # TODO: make this a function
        """Returns if this interface is bound to an edge on this layer"""

        return len(self.edges()) > 0

    def __str__(self):
        return self.__repr__()

    @property
    def _graph(self):
        """Return graph the node belongs to"""

        return self.anm.overlay_nx_graphs[self.overlay_id]

    @property
    def _node(self):
        """Return graph data the node belongs to"""

        return self._graph.node[self.node_id]

    @property
    def _interface(self):
        """Return data dict for the interface"""
        try:
            return self.node.raw_interfaces[self.interface_id]
        except KeyError:
            if not self.node_id in self._graph:
                # node not in overlay
                return
                log.warning("Unable to access interface %s in %s",
                            "node %s not present in overlay" % (self.interface_id,
                                                                self.overlay_id, self.node_id))
                return

            log.warning('Unable to find interface %s in %s'
                        % (self.interface_id, self.node))
            return None

    @property
    def phy(self):
        if self.overlay_id == 'phy':
            return self
        return NmPort(self.anm, 'phy', self.node_id, self.interface_id)

    def __getitem__(self, overlay_id):
        """Returns corresponding interface in specified overlay"""

        if not self.anm.has_overlay(overlay_id):
            log.warning('Trying to access interface %s for non-existent overlay %s'
                        , self, overlay_id)
            return None

        if not self.node_id in self.anm.overlay_nx_graphs[overlay_id]:
            log.debug('Trying to access interface %s for non-existent node %s in overlay %s'
                      , self, self.node_id, self.overlay_id)
            return None

        try:
            return NmPort(self.anm, overlay_id,
                          self.node_id, self.interface_id)
        except KeyError:
            return

    @property
    def is_loopback(self):
        """"""

        return self.category == 'loopback' or self.phy.category == 'loopback'

    @property
    def is_physical(self):
        """"""

        return self.category == 'physical' or self.phy.category == 'physical'

    @property
    def description(self):
        """"""

        return_val = None
        try:
            return_val = self._interface.get('description')
        except IndexError:
            return_val = self.interface_id

        if return_val is not None:
            return return_val

        if self.overlay_id != 'phy':  # prevent recursion
            self.phy._interface.get('description')

    @property
    def is_loopback_zero(self):
        return self.interface_id == 0 and self.is_loopback

    @property
    def category(self):
        """"""

# TODO: make 0 correctly access interface 0 -> copying problem
# TODO: this needs a bugfix rather than the below hard-coded workaround

        if self.interface_id == 0:
            return 'loopback'

        if self.overlay_id == 'input':
            return object.__getattr__(self, 'category')
        elif self.overlay_id != 'phy':

                                        # prevent recursion

            return self.phy._interface.get('category')

        retval = self._interface.get('category')
        if retval:
            return retval

    @property
    def node(self):
        """Returns parent node of this interface"""

        from autonetkit.anm.node import NmNode
        return NmNode(self.anm, self.overlay_id, self.node_id)

    def dump(self):
        return str(self._interface.items())

    def __getattr__(self, key):
        """Returns interface property"""

        try:
            return self._interface.get(key)
        except KeyError:
            return

    def get(self, key):
        """For consistency, node.get(key) is neater
        than getattr(interface, key)"""

        return getattr(self, key)

    def __setattr__(self, key, val):
        """Sets interface property"""

        try:
            self._interface[key] = val
        except KeyError, e:
            log.warning(e)

            # self.set(key, val)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater
        than setattr(interface, key, value)"""

        return self.__setattr__(key, val)

    def edges(self):
        """Returns all edges from node that have this interface ID
        This is the convention for binding an edge to an interface"""

        # edges have _interfaces stored as a dict of {node_id: interface_id, }

        valid_edges = [e for e in self.node.edges() if self.node_id
                       in e.raw_interfaces and e.raw_interfaces[self.node_id]
                       == self.interface_id]
        return list(valid_edges)

    def neighbors(self):
        """Returns interfaces on nodes that are linked to this interface
        Can get nodes using [i.node for i in interface.neighbors()]
        """

        edges = self.edges()
        return [e.dst_int for e in edges]
