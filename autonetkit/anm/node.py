import itertools
import logging
from functools import total_ordering

import autonetkit.log as log
from autonetkit.anm.interface import NmPort
from autonetkit.log import CustomAdapter


@total_ordering
class NmNode(object):

    """NmNode"""

    def __init__(
        self,
        anm,
        overlay_id,
        node_id,
    ):

# Set using this method to bypass __setattr__

        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
# should be able to use _graph from here as anm and overlay_id are defined
        object.__setattr__(self, 'node_id', node_id)
        logger = logging.getLogger("ANK")
        logstring = "Node: %s" % str(self)
        logger = CustomAdapter(logger, {'item': logstring})
        object.__setattr__(self, 'log', logger)

    def __hash__(self):
        """"""

        return hash(self.node_id)

    def __nonzero__(self):
        """Allows for checking if node exists"""

        return self.node_id in self._graph

    def __iter__(self):
        """Shortcut to iterate over the physical interfaces of this node"""

        return self.interfaces(category='physical')

    def __len__(self):
        return len(self.__iter())

    def __eq__(self, other):
        """"""

        try:
            return self.node_id == other.node_id
        except AttributeError:
            return self.node_id == other  # eg compare Node to label

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def loopback_zero(self):
        """"""

        return (i for i in self.interfaces('is_loopback_zero')).next()

    def physical_interfaces(self):
        """"""

        return self.interfaces(category='physical')

    def loopback_interfaces(self):
        """"""

        return self.interfaces(category='loopback')

    def is_multigraph(self):
        return self._graph.is_multigraph()

    def __lt__(self, other):
        """"""

# want [r1, r2, ..., r11, r12, ..., r21, r22] not [r1, r11, r12, r2, r21, r22]
# so need to look at numeric part
        import string
        #TODO: use human sort from StackOverflow

        # sort on label if available
        if self.label is not None:
            self_node_id = self.label
        else:
            self_node_id = self.node_id

        if other.label is not None:
            other_node_id = other.label
        else:
            other_node_id = other_node_id

        try:
            self_node_string = [x for x in self_node_id if x
                                not in string.digits]
            other_node_string = [x for x in self_node_id if x
                                 not in string.digits]
        except TypeError:

            # e.g. non-iterable category, such as an int node_id

            pass
        else:
            if self_node_string == other_node_string:
                self_node_id = """""".join([x for x in self_node_id
                                            if x in string.digits])
                other_node_id = """""".join([x for x in other_node_id
                                             if x in string.digits])
                try:
                    self_node_id = int(self_node_id)
                except ValueError:
                    pass  # not a number
                try:
                    other_node_id = int(other_node_id)
                except ValueError:
                    pass  # not a number

        return (self.asn, self_node_id) < (other.asn, other_node_id)

    def _next_int_id(self):
        """"""

# returns next free interface I

        for int_id in itertools.count(1):  # start at 1 as 0 is loopback
            if int_id not in self._ports:
                return int_id

    # TODO: interface function access needs to be cleaned up

    def _add_interface(
        self,
        description=None,
        category='physical',
        **kwargs
    ):
        """"""

        data = dict(kwargs)

        if self.overlay_id != 'phy' and self['phy']:
            next_id = self['phy']._next_int_id()
            self['phy']._ports[next_id] = {'category': category,
                                             'description': description}

            # TODO: fix this workaround for not returning description from phy
            # graph

            data['description'] = description
        else:
            next_id = self._next_int_id()
            data['category'] = category  # store category on node
            data['description'] = description

        self._ports[next_id] = data
        return next_id

    def add_loopback(self, *args, **kwargs):
        '''Public function to add a loopback interface'''

        interface_id = self._add_interface(category='loopback', *args,
                                           **kwargs)
        return NmPort(self.anm, self.overlay_id,
                                 self.node_id, interface_id)

    def add_interface(self, *args, **kwargs):
        """Public function to add interface"""

        interface_id = self._add_interface(*args, **kwargs)
        return NmPort(self.anm, self.overlay_id,
                                 self.node_id, interface_id)

    def interfaces(self, *args, **kwargs):
        """Public function to view interfaces"""

        def filter_func(interface):
            """Filter based on args and kwargs"""

            return all(getattr(interface, key) for key in args) \
                and all(getattr(interface, key) == val for (key,
                        val) in kwargs.items())

        all_interfaces = iter(NmPort(self.anm,
                              self.overlay_id, self.node_id,
                              interface_id) for interface_id in
                              self._interface_ids())

        retval = (i for i in all_interfaces if filter_func(i))
        return retval

    def interface(self, key):
        """Returns interface based on interface id"""

        try:
            if key.interface_id in self._interface_ids():
                return NmPort(self.anm, self.overlay_id,
                                         self.node_id, key.interface_id)
        except AttributeError:

            # try with key as id

            try:
                if key in self._interface_ids():
                    return NmPort(self.anm, self.overlay_id,
                                             self.node_id, key)
            except AttributeError:

                # no match for either

                log.warning('Unable to find interface %s in %s '
                            % (key, self))
                return None

        # try searching for the "id" attribute of the interface eg
        # GigabitEthernet0/0 if set
        search = list(self.interfaces(id=key))
        # TODO: warn if more than one match ie len > 1
        if len(search):
            return search[0]  # first result

    def _interface_ids(self):
        """Returns interface ids for this node"""
        #TODO: use from this layer, otherwise can get errors iterating when eg vrfs
        return self._ports.keys()

        if self.overlay_id != 'phy' and self['phy']:

            # graph isn't physical, and node exists in physical graph -> use
            # the interface mappings from phy

            return self['phy']._graph.node[self.node_id]['_ports'
                                                      ].keys()
        else:
            try:
                return self._ports.keys()
            except KeyError:
                self.log.debug('No interfaces initialised')
                return []

    @property
    def _ports(self):
        """Returns underlying interface dict"""

        try:
            return self._graph.node[self.node_id]['_ports']
        except KeyError:
            self.log.debug('No interfaces initialised for')
            return []

    @property
    def _graph(self):
        """Return graph the node belongs to"""

        try:
            return self.anm.overlay_nx_graphs[self.overlay_id]
        except Exception, e:
            log.warning("Error accessing overlay %s for node %s: %s" %
                (self.overlay_id, self.node_id, e))

    @property
    def _nx_node_data(self):
        """Return NetworkX node data for the node"""
        try:
            return self._graph.node[self.node_id]
        except Exception, e:
            log.warning("Error accessing node data %s for node %s: %s" %
                (self.overlay_id, self.node_id, e))

    def is_router(self):
        """Either from this graph or the physical graph"""

        return self.device_type == 'router' or self['phy'].device_type \
            == 'router'

    def is_device_type(self, device_type):
        """Generic user-defined cross-overlay search for device_type
        either from this graph or the physical graph"""

        return self.device_type == device_type or self['phy'].device_type \
            == device_type

    def is_switch(self):
        """Returns if device is a switch"""

        return self.device_type == 'switch' or self['phy'].device_type \
            == 'switch'

    def is_server(self):
        """Returns if device is a server"""

        return self.device_type == 'server' or self['phy'].device_type \
            == 'server'

    def is_l3device(self):
        """Layer 3 devices: router, server, cloud, host
        ie not switch
        """
        return self.is_router() or self.is_server()

    def __getitem__(self, key):
        """Get item key"""

        return NmNode(self.anm, key, self.node_id)

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._ports

    @raw_interfaces.setter
    def raw_interfaces(self, value):
     self._ports = value

    @property
    def asn(self):
        """Returns ASN of this node"""
        # TODO: make a function (not property)

        try:
            return self._graph.node[self.node_id]['asn']  # not in this graph
        except KeyError:

            # try from phy

            try:
                return self.anm.overlay_nx_graphs['phy'
                                                  ].node[self.node_id]['asn']
            except KeyError:
                if self.node_id not in self.anm.overlay_nx_graphs['phy'
                                                                  ]:
                    message = \
                        'Node id %s not found in physical overlay' \
                        % self.node_id
                    if self.overlay_id == 'input':

                        # don't warn, most likely node not copied across

                        log.debug(message)
                    else:
                        log.warning(message)
                    return

    @asn.setter
    def asn(self, value):
        # TODO: make a function (not property)

        # TODO: double check this logic

        try:
            self.anm.overlay_nx_graphs['phy'].node[self.node_id]['asn'
                                                                 ] = value
        except KeyError:

            # set ASN directly on the node, eg for collision domains

            self._graph.node[self.node_id]['asn'] = value

    @property
    def id(self):
        """Returns node id"""

        return self.node_id

    @property
    def _overlay(self):
        """Access overlay graph for this node"""

        from autonetkit.anm.graph import NmGraph
        return NmGraph(self.anm, self.overlay_id)

    def degree(self):
        """Returns degree of node"""

        return self._graph.degree(self.node_id)



    def neighbors(self, *args, **kwargs):
        """Returns neighbors of node"""

        neighs = list(NmNode(self.anm, self.overlay_id, node)
                    for node in self._graph.neighbors(self.node_id))

        return self._overlay.filter(neighs, *args, **kwargs)

    def neighbor_interfaces(self, *args, **kwargs):

        # TODO: implement filtering for args and kwargs

        if len(args) or len(kwargs):
            log.warning("Attribute-based filtering not currently",
             "supported for neighbor_interfaces")

        return iter(edge.dst_int for edge in self.edges())

    @property
    # TODO: make a function to reflect dynamic nature: constructed from other
    # attributes
    def label(self):
        """Returns node label (mapped from ANM)"""

        return self.__repr__()

    def dump(self):
        """Dump attributes of this node"""

        data = dict(self._nx_node_data)
        try:
            del data['_ports']
        except KeyError:
            pass # no interfaces set
        return str(data)

    def edges(self, *args, **kwargs):
        """Edges to/from this node"""

        return list(self._overlay.edges(self, *args, **kwargs))

    def __str__(self):
        return str(self.__repr__())

    def __repr__(self):
        """Try label if set in overlay, otherwise from physical,
        otherwise node id"""

        try:
            return self.anm.node_label(self)
        except KeyError:
            try:
                return self._graph.node[self.node_id]['label']
            except KeyError:
                return self.node_id  # node not in physical graph
        except AttributeError:
            return self.node_id

    def __getattr__(self, key):
        """Returns node property
        This is useful for accesing attributes passed through from graphml"""
        #TODO: refactor/document this logic

        try:
            node_data = self._graph.node[self.node_id]
        except KeyError:
            # TODO: only carry out this logic if "Strict mode"
            if key == "device_type":
                # TODO: tidy accessors so this doesn't occur, and remove the
                # suppress
                return
            self.log.debug("Cannot access %s: node not present in %s"
                           % (key, self.overlay_id))
            return
        else:
            try:
                result = node_data[key]
                return result
            except KeyError:
                if key == "device_type":
                    return self['phy'].device_type
                if key == "device_subtype":
                    return self['phy'].device_subtype

                # from http://stackoverflow.com/q/2654113
                self.log.debug(
                    "Accessing unset attribute %s in %s" % (key,
                        self.overlay_id))
                return

        # map through to phy

    def get(self, key):
        """For consistency, node.get(key) is neater than getattr(node, key)"""

        return getattr(self, key)

    def __setattr__(self, key, val):
        """Sets node property
        This is useful for accesing attributes passed through from graphml"""

        """TODO:
        TODO: look at mapping the object __dict__ straight to the graph.node[self.node_id]
        TODO: fix wrt using @x.setter won't work due to following:
        as per
        http://docs.python.org/2/reference/datamodel.html#customizing-attribute-access
        """

        # TODO: fix workaround for asn

        if key == 'asn':
            object.__setattr__(self, 'asn', val)

        if key == 'raw_interfaces':
            object.__setattr__(self, 'raw_interfaces', val)

        try:
            self._graph.node[self.node_id][key] = val
        except KeyError:
            self._graph.add_node(self.node_id)
            self.set(key, val)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater
        than setattr(node, key, value)"""

        return self.__setattr__(key, val)
