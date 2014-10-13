import functools
import logging
import string

import autonetkit.log as log
from autonetkit.log import CustomAdapter
from autonetkit.nidb.config_stanza import ConfigStanza
from autonetkit.nidb.interface import DmInterface
import autonetkit.log as log


@functools.total_ordering
class DmNode(object):

    """API to access overlay graph node in network"""

    def __init__(self, nidb, node_id):
        # Set using this method to bypass __setattr__
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)
        #logger = logging.getLogger("ANK")
        # TODO: also pass the node object to the logger for building custom output lists
        # ie create a special handler that just outputs the specific node/link/interface errors
        #logstring = "Node: %s" % str(self)
        #logger = CustomAdapter(logger, {'item': logstring})
        logger = log
        object.__setattr__(self, 'log', logger)

    # TODO: make a json objct that returns keys that aren't logs, etc - filter
    # out

    def __repr__(self):
        return self._node_data['label']

    # TODO: add a dump method - needed with str()?

    def add_stanza(self, name, **kwargs):
        # TODO: decide if want shortcut for *args to set to True
        if self.get(name):
            value = self.get(name)
            if isinstance(value, ConfigStanza):
                # Don't recreate
                self.log.debug("Stanza %s already exists" % name)
                return value
            else:
                # TODO: remove? - as shouldn't reach here now? GH-186
                log.warning(
                    "Creating stanza: %s already set as %s for %s" % (name, type(value), self))

        stanza = ConfigStanza(**kwargs)
        self.__setattr__(name, stanza)
        return stanza

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        try:
            return self.node_id == other.node_id
        except AttributeError:
            # TODO: check why comparing against strings - if in overlay
            # graph...
            return self.node_id == other

    def interface(self, key):
        # TODO: also need to allow access interface for nidb and search on
        # (node, interface id) tuple
        try:
            interface_id = key.interface_id  # eg extract from interface
        except AttributeError:
            interface_id = key  # eg string

        return DmInterface(self.nidb, self.node_id, interface_id)

    @property
    def _ports(self):
        """Returns underlying interface dict"""
        try:
            return self._graph.node[self.node_id]["_ports"]
        except KeyError:
            log.debug("No interfaces initialised for %s" % self)
            return

    @property
    def _next_int_id(self):
        """"""
# returns next free interface ID
        import itertools
        for int_id in itertools.count(1):  # start at 1 as 0 is loopback
            if int_id not in self._ports:
                return int_id

    def add_interface(self, description=None, category="physical", *args,  **kwargs):
        """Public function to add interface"""
        data = dict(kwargs)
        interface_id = self._next_int_id
        data['category'] = category  # store category on node
        data['description'] = description
        self._ports[interface_id] = data

        return DmInterface(self.nidb, self.node_id, interface_id)

    @property
    def _interface_ids(self):
        return self._ports.keys()

    @property
    def interfaces(self):
        # TODO: make not a property
        """Called by templates, sorts by ID"""
        int_list = self.get_interfaces()

        # Put loopbacks before physical interfaces
        type_index = {"loopback": 0, "physical": 1}
        # TODO: extend this based on medium category, etc

        int_list = sorted(int_list, key=lambda x: x.id)
        int_list = sorted(int_list, key=lambda x: type_index[x.category])
        return int_list

    def physical_interfaces(self):
        return self.get_interfaces(category="physical")

    def loopback_interfaces(self):
        return self.get_interfaces(category="loopback")

    def get_interfaces(self, *args, **kwargs):
        """Public function to view interfaces

        Temporary function name until Compiler/DeviceModel/Templates
        move to using "proper" interfaces"""
        def filter_func(interface):
            """Filter based on args and kwargs"""
            return (
                all(getattr(interface, key) for key in args) and
                all(getattr(
                    interface, key) == val for key, val in kwargs.items())
            )

        all_interfaces = iter(DmInterface(self.nidb,
                                          self.node_id, interface_id)
                              for interface_id in self._interface_ids)
        retval = (i for i in all_interfaces if filter_func(i))
        return retval

    @property
    def loopback_zero(self):
        return (i for i in self.interfaces if i.is_loopback_zero).next()

    @property
    def raw_interfaces(self):
        """Direct access to the interfaces dictionary, used by ANK modules"""
        return self._ports

    @raw_interfaces.setter
    def raw_interfaces(self, value):
        self._ports = value

    @property
    def _graph(self):
        return self.nidb.raw_graph()

    def degree(self):
        return self._graph.degree(self.node_id)

    def neighbors(self):
        return iter(DmNode(self.nidb, node)
                    for node in self._graph.neighbors(self.node_id))

    def __setstate__(self, state):
        (nidb, node_id) = state
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)

    def __lt__(self, other):
        # TODO: use human sort from StackOverflow

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

            # e.g. non-iterable type, such as an int node_id

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

    @property
    def _node_data(self):
        return self.nidb.raw_graph().node[self.node_id]

    def dump(self):
        # return str(self._node_data)
        import pprint
        pprint.pprint(self._node_data)

    def __nonzero__(self):
        return self.node_id in self.nidb.raw_graph()

    def is_router(self):
        return self.device_type == "router"

    def is_device_type(self, device_type):
        """Generic user-defined cross-overlay search for device_type for consistency with ANM"""
        return self.device_type == device_type

    def is_switch(self):
        return self.device_type == "switch"

    def is_server(self):
        return self.device_type == "server"

    def is_l3device(self):
        """Layer 3 devices: router, server, cloud, host
        ie not switch
        """
        # TODO: need to check for cloud, host
        return self.is_router() or self.is_server()

    def edges(self, *args, **kwargs):
        # TODO: want to add filter for *args and **kwargs here too
        return self.nidb.edges(self, *args, **kwargs)

    @property
    def id(self):
        return self.node_id

    @property
    def label(self):
        return self.__repr__()

    def get(self, key):
        return getattr(self, key)

    def __getattr__(self, key):
        """Returns edge property"""
        data = self._node_data.get(key)

        # TODO: remove once deprecated DmNode_category
        if isinstance(data, ConfigStanza):
            return data

        return data

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._node_data[key] = val
        # return DmNode_category(self.nidb, self.node_id, key)

    def __iter__(self):
        return iter(self._node_data)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater
        than setattr(node, key, value)"""
        return self.__setattr__(key, val)
