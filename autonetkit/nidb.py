import networkx as nx
import pprint
import collections
import time
import autonetkit.log as log
import ank_json
import functools
import string

try:
    import cPickle as pickle
except ImportError:
    import pickle

class interface_data_dict(collections.MutableMapping):
    """A dictionary which allows access as dict.key as well as dict['key']
    Based on http://stackoverflow.com/questions/3387691
    only allows read only acess
    """

    def __repr__(self):
        return ", ".join(self.store.keys())

    def __init__(self, data):
#Note this won't allow updates in place
        self.store = data
        #self.data = parent[index]
        #self.update(dict(*args, **kwargs)) # use the free update to set keys
#TODO: remove duplicate of self.store and parent

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[key] = value # store locally

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key

    def __getattr__(self, key):
        return self.store.get(key)

    def __setattr__(self, key, value):
        if key == "store":
            object.__setattr__(self, 'store', value)
        else:
            self.store[key] = value # store locally

    def dump(self):
        return self.store

class overlay_data_dict(collections.MutableMapping):
    """A dictionary which allows access as dict.key as well as dict['key']
    Based on http://stackoverflow.com/questions/3387691
    """

    def __repr__(self):
        return ", ".join(self.store.keys())

    def __init__(self, parent, index, data):
#Note this won't allow updates in place
        self.parent = parent
        self.index = index
        self.store = data
        #self.data = parent[index]
        #self.update(dict(*args, **kwargs)) # use the free update to set keys
#TODO: remove duplicate of self.store and parent

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[key] = value # store locally
        self.parent._update_dict(self.index, key, value)

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        return key

    def __getattr__(self, key):
        return self.store.get(key)

#TODO: fix __setattr__ so doesn't cause recursion - and so doesn't silently not set values in compiler
#same as for interfaces

    def dump(self):
        return self.store

class overlay_data_list_of_dicts(object):
    #NOTE: this is just a presentation of the data - so can't modify the original
# but can do in place sort, append, etc
    #TODO: make this inherit from list - so can remove .append() etc
    def __init__(self, parent, key):
        self.parent = parent
        self.key = key
        self.data = parent[key]

    def __getstate__(self):
        return (self.data)

    def __getnewargs__(self):
        return ()

    def __setstate__(self, state):
        self.data = state

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return str(self.data)

    def __nonzero__(self):
        """Allows for checking if data exists """
        if len(self.data):
            return True
        else:
            return False

    def dump(self):
        return self.data

    def append(self, *args, **kwargs):
        if args:
            item = args[0]
            self.data.append(item)
        if kwargs:
            self.data.append(kwargs)

    def sort(self, key, reverse = False):
        #TODO: allow multiple keys
        self.data.sort(key = lambda x: x.get(key), reverse = reverse)

    def __iter__(self):
        #TODO: want to introduce some sorting here.... how?
        #return iter(overlay_data_dict(self, item) for item in self.data)
        for index, item in enumerate(self.data):
            yield overlay_data_dict(self, index, item)

    def __getitem__(self, index):
        return overlay_data_dict(self, index, self.data[index])

    def _update_dict(self, index, key, value):
        """Used to feed changes from overlay_data_dict back"""
        self.parent[self.key][index][key] = value


class overlay_interface(object):
    def __init__(self, nidb, node_id, interface_id):
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'interface_id', interface_id)

    def __key(self):
        # based on http://stackoverflow.com/q/2909106
        return (self.interface_id, self.node_id)

    def __hash__(self):
        """"""
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __repr__(self):
        description = self.description or self.interface_id
        return "(%s, %s)" % (self.node_id, description)

    def __nonzero__(self):
        """Allows for checking if node exists
        """
        return len(self._interface) > 0  # if interface data set

    def __str__(self):
        return self.__repr__()

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.nidb._graph

    @property
    def _node(self):
        """Return graph the node belongs to"""
        return self._graph.node[self.node_id]

    @property
    def _interface(self):
        """Return graph the node belongs to"""
        return self._node["_interfaces"][self.interface_id]

    @property
    def is_loopback(self):
        """"""
        return self.type == "loopback" or self.phy.type == "loopback"

    @property
    def is_physical(self):
        """"""
        return self.type == "physical" or self.phy.type == "physical"

    @property
    def description(self):
        """"""
        return self._interface.get("description")

    @property
    def is_loopback_zero(self):
        # by convention, loopback_zero is at id 0
        return self.interface_id == 0 and self.is_loopback

    @property
    def node(self):
        """Returns parent node of this interface"""
        return nidb_node(self.nidb, self.node_id)

    def dump(self):
        return str(self._interface.items())

    def dict(self):
        """Returns shallow copy of dictionary used.
        Note not a deep copy: modifying values may have impact"""
        return dict(self._interface.items())

    def __getattr__(self, key):
        """Returns interface property"""
        try:
            data = self._interface.get(key)
        except KeyError:
            return

        if isinstance(data, dict):
            return interface_data_dict(data)

        return data

    def get(self, key):
        """For consistency, node.get(key) is neater 
        than getattr(interface, key)"""
        return getattr(self, key)

    def __setattr__(self, key, val):
        """Sets interface property"""
        try:
            self._interface[key] = val
        except KeyError:
            self.set(key, val)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater
        than setattr(interface, key, value)"""
        return self.__setattr__(key, val)

    def edges(self):
        """Returns all edges from node that have this interface ID
        This is the convention for binding an edge to an interface"""
        # edges have _interfaces stored as a dict of {node_id: interface_id, }
        valid_edges = [e for e in self.node.edges()
                if self.node_id in e._interfaces
                and e._interfaces[self.node_id] == self.interface_id]
        return valid_edges

class overlay_edge_accessor(object):
#TODO: do we even need this?
    """API to access overlay edges in NIDB"""
#TODO: fix consistency between node_id (id) and edge (overlay edge)
    def __init__(self, nidb, edge):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'edge', edge)

    def __repr__(self):
        #TODO: make this list overlays the node is present in
        return "Overlay edge accessor: %s" % self.edge

    def __getnewargs__(self):
        return ()

    def __getattr__(self, overlay_id):
        """Access overlay edge"""
#TODO: check on returning list or single edge if multiple found with same id (eg in G_igp from explode)
        edge = self.nidb.edge(self.edge)
        return edge

class overlay_edge(object):
    """API to access edge in nidb"""
    def __init__(self, nidb, src_id, dst_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)

    def __repr__(self):
        return "(%s, %s)" % (self.src, self.dst)

    def __getstate__(self):
        return (self.nidb, self.src_id, self.dst_id)

    def __getnewargs__(self):
        return ()

    def __setstate__(self, state):
        (nidb, src_id, dst_id) = state
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)

    @property
    def src(self):
        return nidb_node(self.nidb, self.src_id)

    @property
    def dst(self):
        return nidb_node(self.nidb, self.dst_id)

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])

    def __nonzero__(self):
        """Allows for checking if edge exists
        """
        try:
            self._graph[self.src_id][self.dst_id]
            return True
        except KeyError:
            return False

    @property
    def overlay(self):
        """Access node in another overlay graph"""
        return overlay_edge_accessor(self.nidb, self)

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.nidb._graph

    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)"""
        return self.__getattr__(key)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._graph[self.src_id][self.dst_id].get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._graph[self.src_id][self.dst_id][key] = val

class overlay_node_accessor(object):
#TODO: do we even need this?
    def __init__(self, nidb, node_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)

    def __repr__(self):
        #TODO: make this list overlays the node is present in
        return "Overlay accessor for: %s" % self.nidb

    def __getattr__(self, key):
        """Access category"""
        return nidb_node_category(self.nidb, self.node_id, key)

class nidb_node_subcategory(object):
    def __init__(self, nidb, node_id, category_id, subcategory_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'category_id', category_id)
        object.__setattr__(self, 'subcategory_id', subcategory_id)

    @property
    def _data(self):
        return 

    def __repr__(self):
        return self.nidb._graph.node[self.node_id][self.category_id][self.subcategory_id]

class nidb_node_category(object):
    #TODO: make this custom dict like above?
    def __init__(self, nidb, node_id, category_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'category_id', category_id)

    def __getstate__(self):
        return (self.nidb, self.node_id, self.category_id)

    def __getnewargs__(self):
        return ()

    def __setstate__(self, state):
        """For pickling"""
        self._overlays = state
        (nidb, node_id, category_id) = state
#TODO: call to self __init__ ???
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'category_id', category_id)

    def __repr__(self):
        return str(self._node_data.get(self.category_id))

    def __nonzero__(self):
        """Allows for accessing to set attributes
        This simplifies templates
        but also for easy check, eg if sw1.bgp can return False if category not set
        but can later do r1.bgp.attr = value
        """
        if self.category_id in self._node_data:
            if self._node_data[self.category_id]:
                return True
        return False

    @property
    def _category_data(self):
        try:
            return self._node_data[self.category_id]
        except KeyError:
            log.debug("No category_id %s in node %s" % (self.category_id, self.node_id))

    def __getitem__(self, key):
        """Used to access the data directly. calling node.key returns wrapped data for templates"""
        return self._category_data[key]

    @property
    def _node_data(self):
        return self.nidb._graph.node[self.node_id]

    def __getattr__(self, key):
        """Returns edge property"""
#TODO: allow appending if non existent: so can do node.bgp.session.append(data)
        try:
            data = self._category_data.get(key)
        except AttributeError:
            return None # key doesn't exist
        try:
            [item.keys() for item in data]
            #print "from nidb_node_category", self.nidb, self.node_id, self.category_id
            return overlay_data_list_of_dicts(self._category_data, key)
        except AttributeError:
            pass # not a dict
        except TypeError:
            #Supress warning as could occur if this element is a primitive rather than a dict
            #eg a boolean, which is valid
            # TODO: revisit this
            #log.debug("Access unset key %s in %s %s" % (key, self.node_id, self.category_id))
            pass # also not a dict
        return data

    def dump(self):
        return str(self._node_data)

    def __setattr__(self, key, val):
        """Sets edge property"""
        try:
            self._node_data[self.category_id][key] = val
        except KeyError:
            self._node_data[self.category_id] = {} # create dict for this data category
            setattr(self, key, val)

#TODO: this should also inherit from collections, so don't break __getnewargs__ etc

@functools.total_ordering
class nidb_node(object):
    """API to access overlay graph node in network"""

    def __init__(self, nidb, node_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)

    def __repr__(self):
        return self._node_data['label']

    def __getnewargs__(self):
        return ()

    def __getstate__(self):
        return (self.nidb, self.node_id)

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        try:
            return self.node_id == other.node_id
        except AttributeError:
            return self.node_id == other #TODO: check why comparing against strings - if in overlay graph...

    def interface(self, key):
        #TODO: also need to allow access interface for nidb and search on (node, interface id) tuple
        try:
            interface_id = key.interface_id # eg extract from interface
        except AttributeError:
            interface_id = key # eg string

        return overlay_interface(self.nidb, self.node_id, interface_id)


    @property
    def _interfaces(self):
        """Returns underlying interface dict"""
        try:
            return self._graph.node[self.node_id]["_interfaces"]
        except KeyError:
            log.debug("No interfaces initialised for %s" % self)
            return 

    @property
    def _next_int_id(self):
        """"""
# returns next free interface ID
        import itertools
        for int_id in itertools.count(1):  # start at 1 as 0 is loopback
            if int_id not in self._interfaces:
                return int_id

    def add_interface(self, description = None, type = "physical", *args,  **kwargs):
        """Public function to add interface"""
        data = dict(kwargs)
        interface_id = self._next_int_id
        data['type'] = type  # store type on node
        data['description'] = description
        self._interfaces[interface_id] = data

        return overlay_interface(self.nidb, self.node_id, interface_id)

    @property
    def _interface_ids(self):
        return self._graph.node[self.node_id]["_interfaces"].keys()

    @property
    def interfaces(self):
        """Called by templates, sorts by ID"""
        int_list = self.get_interfaces()

        # Put loopbacks before physical interfaces
        type_index = {"loopback": 0, "physical": 1}
        #TODO: extend this based on medium type, etc

        int_list = sorted(int_list, key = lambda x: x.id)
        int_list = sorted(int_list, key = lambda x: type_index[x.type])
        return int_list

    @property
    def physical_interfaces(self):
        return self.get_interfaces(type = "physical")

    @property
    def loopback_interfaces(self):
        return self.get_interfaces(type = "loopback")

    def get_interfaces(self, *args, **kwargs):
        """Public function to view interfaces

        Temporary function name until Compiler/NIDB/Templates
        move to using "proper" interfaces"""
        def filter_func(interface):
            """Filter based on args and kwargs"""
            return (
                all(getattr(interface, key) for key in args) and
                all(getattr(
                    interface, key) == val for key, val in kwargs.items())
            )

        all_interfaces = iter(overlay_interface(self.nidb, 
            self.node_id, interface_id)
            for interface_id in self._interface_ids)
        retval = (i for i in all_interfaces if filter_func(i))
        return retval

    @property
    def loopback_zero(self):
        return (i for i in self.interfaces if i.is_loopback_zero).next()

    @property
    def _graph(self):
        return self.nidb._graph

    def degree(self):
        return self._graph.degree(self.node_id)

    def neighbors(self):
        return iter(nidb_node(self.nidb, node)
                for node in self._graph.neighbors(self.node_id))

    def __setstate__(self, state):
        (nidb, node_id) = state
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)

    def __lt__(self, other):
# want [r1, r2, ..., r11, r12, ..., r21, r22] not [r1, r11, r12, r2, r21, r22]
# so need to look at numeric part
#TODO: make this work with ASN (which isn't always imported to NIDB)
        self_node_id = self.node_id
        other_node_id = other.node_id
        self_node_string = [x for x in self.node_id if x not in string.digits]
        other_node_string = [x for x in self.node_id if x not in string.digits]
        if self_node_string == other_node_string:
            self_node_id = "".join([x for x in self.node_id if x in string.digits])
            other_node_id = "".join([x for x in other.node_id if x in string.digits])
            try:
                self_node_id = int(self_node_id)
            except ValueError:
                pass # not a number
            try:
                other_node_id = int(other_node_id)
            except ValueError:
                pass # not a number

        return ((self.asn, self_node_id) < (other.asn, other_node_id))

    @property
    def _node_data(self):
        return self.nidb._graph.node[self.node_id]

    def dump(self):
        #return str(self._node_data)
        import pprint
        pprint.pprint(self._node_data)

    def __nonzero__(self):
        return self.node_id in self.nidb._graph

    @property
    def is_router(self):
        return self.device_type == "router"

    @property
    def is_switch(self):
        return self.device_type == "switch"

    @property
    def is_server(self):
        return self.device_type == "server"

    @property
    def is_l3device(self):
        """Layer 3 devices: router, server, cloud, host
        ie not switch
        """
        return self.is_router or self.is_server

    def edges(self, *args, **kwargs):
        #TODO: want to add filter for *args and **kwargs here too
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
        try:
            [item.keys() for item in data]
            #print "from nidb node", self.nidb, self.node_id, key
            return overlay_data_list_of_dicts(self._node_data, key)
        except TypeError:
            pass # Not set yet
        except AttributeError:
            pass # not a dict

        try:
            data.keys() 
            return nidb_node_category(self.nidb, self.node_id, key)
        except TypeError:
            pass # Not set yet
        except AttributeError:
            pass # not a dict

        if data:
            return data
        else:
            return nidb_node_category(self.nidb, self.node_id, key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._node_data[key] = val
        #return nidb_node_category(self.nidb, self.node_id, key)

    def __iter__(self):
        return iter(self._node_data)

    @property
    def overlay(self):
        return overlay_node_accessor(self.nidb, self.node_id)

class nidb_graph_data(object):
    """API to access overlay graph data in network"""

    def __init__(self, nidb):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)

    def __repr__(self):
        return "NIDB data: %s" % self.nidb._graph.graph

    def __getattr__(self, key):
        """Returns edge property"""
        return self.nidb._graph.graph.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self.nidb._graph.graph[key] = val

#TODO: make this inherit same overlay base as overlay_graph for add nodes etc properties
# but not the degree etc

class lab_topology(object):
    """API to access lab topology in network"""

    def __init__(self, nidb, topology_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'topology_id', topology_id)

    def __repr__(self):
        return "Lab Topology: %s" % self.topology_id

    @property
    def _topology_data(self):
        return self.nidb._graph.graph['topologies'][self.topology_id]

    def dump(self):
        return str(self._topology_data)

    def __getattr__(self, key):
        """Returns topology property"""
        data = self._topology_data.get(key)
        try:
            [item.keys() for item in data]
#TODO: replace this with an OrderedDict
            #print "from lab_topology", self.nidb, self.topology_id, key
            return overlay_data_list_of_dicts(self._topology_data, key)
        except AttributeError:
            pass # not a dict
        except TypeError:
            pass # also not a dict
        return data
        return self._topology_data.get(key)

    def __setattr__(self, key, val):
        """Sets topology property"""
        self._topology_data[key] = val

class NIDB_base(object):
    #TODO: inherit common methods from same base as overlay
    def __init__(self):
        pass

#TODO: make optional argument to take serialized file on init, and restore from this

    def __getstate__(self):
        return self._graph

    def __setstate__(self, state):
        self._graph = state

    def __getnewargs__(self):
        return ()

    def __repr__(self):
        return "nidb"

    def dump(self):
        #TODO: adapt the json version?
        return "%s %s %s" % (
                pprint.pformat(self._graph.graph),
                pprint.pformat(self._graph.nodes(data=True)),
                pprint.pformat(self._graph.edges(data=True))
                )

    def save(self, timestamp = True, use_gzip = True):
        import os
        import gzip
        archive_dir = os.path.join("versions", "nidb")
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

        data = ank_json.ank_json_dumps(self._graph)
#TODO: should this use the ank_json.jsonify_nidb() ?
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
        return overlay_interface(self,
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
            log.warning("No previous NIDB saved. Please compile new NIDB")
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

    def copy_graphics(self, G_graphics):
        """Transfers graphics data from anm to nidb"""
        for node in self:
            graphics_node = G_graphics.node(node)
            node.graphics.x = graphics_node.x
            node.graphics.y = graphics_node.y
            node.graphics.device_type = graphics_node.device_type
            node.graphics.device_subtype = graphics_node.device_subtype
            node.device_type = graphics_node.device_type
            node.device_subtype = graphics_node.device_subtype

    def __len__(self):
        return len(self._graph)

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
        all_edges = iter(overlay_edge(self, src, dst)
                for src, dst in self._graph.edges(nbunch)
                )
        return (edge for edge in all_edges if filter_func(edge))

    def node(self, key):
        """Returns node based on name
        This is currently O(N). Could use a lookup table"""
#TODO: check if node.node_id in graph, if so return wrapped node for this...
# returns node based on name
        try:
            if key.node_id in self._graph:
                return nidb_node(self, key.node_id)
        except AttributeError:
            # doesn't have node_id, likely a label string, search based on this label
            for node in self:
                if str(node) == key:
                    return node
                elif node.id == key:
                    # label could be "a b" -> "a_b" (ie folder safe, etc)
                    #TODO: need to fix this discrepancy
                    return node
            print "Unable to find node", key, "in", self
            return None

    def edge(self, edge_to_find):
        """returns edge in this graph with same src and same edge_id"""
        src_id = edge_to_find.src_id
        search_id = edge_to_find.edge_id
#TODO: if no edge_id then search for src, dst pair

        for src, dst in self._graph.edges_iter(src_id):
            try:
                if self._graph[src][dst]['edge_id'] == search_id:
                    return overlay_edge(self, src, dst)
            except KeyError:
                pass # no edge_id for this edge

    @property
    def data(self):
        return nidb_graph_data(self)

    def update(self, nbunch, **kwargs):
        for node in nbunch:
            for (category, key), value in kwargs.items():
                node.category.set(key, value)

    def nodes(self, *args, **kwargs):
        result = self.__iter__()
        if len(args) or len(kwargs):
            result = self.filter(result, *args, **kwargs)
        return result

    def routers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be router"""
        kwargs['device_type'] = 'router'
        return self.nodes(*args, **kwargs)

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

    def add_nodes_from(self, nbunch, retain=[], **kwargs):
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
            log.warn("Cannot add node ids directly to NIDB: must add overlay nodes")
        self._graph.add_nodes_from(nbunch, **kwargs)

        for node in nodes_to_add:
            #TODO: add an interface_retain for attributes also
            int_dict = {i.interface_id: {'type': i.type, 
                'description': i.description,
                'layer': i.overlay_id} for i in node.interfaces()}
            int_dict = {i.interface_id: {'type': i.type,
                'description': i.description,
                } for i in node.interfaces()}
            self._graph.node[node.node_id]["_interfaces"] = int_dict

    def add_edge(self, src, dst, retain=[], **kwargs):
        self.add_edges_from([(src, dst)], retain, **kwargs)

    def add_edges_from(self, ebunch, retain=[], **kwargs):
        #TODO: need to retain interface references
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        edges_to_add = ebunch # retain for interface copying

        #TODO: need to test if given a (id, id) or an edge overlay pair... use try/except for speed
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

        #TODO: decide if want to allow nodes to be created when adding edge if not already in graph
        self._graph.add_edges_from(ebunch, **kwargs)
        for edge in edges_to_add:
            # copy across interface bindings
            self._graph[edge.src.node_id][edge.dst.node_id]['_interfaces'] = edge._interfaces

    def __iter__(self):
        return iter(nidb_node(self, node)
                for node in self._graph)

class lab_topology_accessor(object):
    """API to access overlay graphs in ANM"""
    def __init__(self, nidb):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'nidb', nidb)

    @property
    def topologies(self):
        return self.self.nidb._graph.graph['topologies']

#TODO: add iter similarly to anm overlay accessor
    def __iter__(self):
        return iter(lab_topology(self.nidb, key) for key in self.topologies.keys())

    def __repr__(self):
        return "Available lab topologies: %s" % ", ".join(sorted(self.topologies.keys()))

    def __getattr__(self, key):
        """Access overlay graph"""
        return lab_topology(self.nidb, key)

    def __getitem__(self, key):
        """Access overlay graph"""
        return lab_topology(self.nidb, key)

    def get(self, key):
        return getattr(self, key)

    def add(self, key):
        self.topologies[key] = {}
        return lab_topology(self.nidb, key)

class NIDB(NIDB_base):
    def __init__(self):
        self._graph = nx.Graph() # only for connectivity, any other information stored on node
        self._graph.graph['topologies'] = collections.defaultdict(dict)
        self._graph.graph['timestamp'] = time.strftime("%Y%m%d_%H%M%S", time.localtime())

    @property
    def timestamp(self):
        return self._graph.graph['timestamp']

    @property
    def topology(self):
        return lab_topology_accessor(self)

    def subgraph(self, nbunch, name = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return overlay_subgraph(self._graph.subgraph(nbunch), name)

    def boundary_nodes(self, nbunch, nbunch2 = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return iter(nidb_node(self, node)
                for node in nx.node_boundary(self._graph, nbunch, nbunch2))

    def boundary_edges(self, nbunch, nbunch2 = None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return iter(overlay_edge(self, src, dst)
                for (src, dst) in nx.edge_boundary(self._graph, nbunch, nbunch2))

class overlay_subgraph(NIDB_base):
    def __init__(self, graph, name = None):
        #TODO: need to refer back to the source nidb
        self._graph = graph # only for connectivity, any other information stored on node
        self._name = name
    def __repr__(self):
        return "nidb: %s" % self._name
