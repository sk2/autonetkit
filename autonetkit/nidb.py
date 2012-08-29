import networkx as nx
import pprint
import collections
import time

class overlay_data_dict(collections.MutableMapping):
    """A dictionary which allows access as dict.key as well as dict['key']
    Based on http://stackoverflow.com/questions/3387691
    """

    def __repr__(self):
        return ", ".join(self.store.keys())

    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs)) # use the free update to set keys

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value

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

class overlay_data_list_of_dicts(object):
    def __init__(self, data):
        self.data = data

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

    def __iter__(self):
        #TODO: want to introduce some sorting here.... how?
        return iter(overlay_data_dict(item) for item in self.data)

class overlay_edge_accessor(object):
#TODO: do we even need this?
    """API to access overlay nodes in ANM"""
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
        print "state has cat id", self.category_id
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
            return True
        return False

    @property
    def _category_data(self):
        return self._node_data[self.category_id]

    def __getitem__(self, key):
        """Used to access the data directly. calling node.key returns wrapped data for templates"""
        return self._category_data[key]

    @property
    def _node_data(self):
        return self.nidb._graph.node[self.node_id]

    def __getattr__(self, key):
        """Returns edge property"""
#TODO: allow appending if non existent: so can do node.bgp.session.append(data)
        data = self._category_data.get(key)
        try:
            [item.keys() for item in data]
#TODO: replace this with an OrderedDict
            return overlay_data_list_of_dicts(data)
        except AttributeError:
            pass # not a dict
        except TypeError:
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

    def __setstate__(self, state):
        (nidb, node_id) = state
        object.__setattr__(self, 'nidb', nidb)
        object.__setattr__(self, 'node_id', node_id)

    @property
    def _node_data(self):
        return self.nidb._graph.node[self.node_id]

    def dump(self):
        return str(self._node_data)


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
            return overlay_data_list_of_dicts(data)
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
            return overlay_data_list_of_dicts(data)
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

    def __getstate__(self):
        return self._graph

    def __setstate__(self, state):
        self._graph = state

    def __getnewargs__(self):
        return ()

    def __repr__(self):
        return "nidb"

    def dump(self):
        return "%s %s %s" % (
                pprint.pformat(self._graph.graph),
                pprint.pformat(self._graph.nodes(data=True)),
                pprint.pformat(self._graph.edges(data=True))
                )

    #TODO: add restore function

    def save(self):
        import os
        pickle_dir = os.path.join("versions", "nidb")
        if not os.path.isdir(pickle_dir):
            os.makedirs(pickle_dir)

        pickle_file = "nidb_%s.pickle.tar.gz" % self.timestamp
        pickle_path = os.path.join(pickle_dir, pickle_file)
        nx.write_gpickle(self._graph, pickle_path)

    @property
    def name(self):
        return self.__repr__()

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

        if len(retain):
            add_nodes = []
            for n in nbunch:
                data = dict( (key, n.get(key)) for key in retain)
                add_nodes.append( (n.node_id, data) )
            nbunch = add_nodes
        else:
            nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        self._graph.add_nodes_from(nbunch, **kwargs)

    def add_edge(self, src, dst, retain=[], **kwargs):
        self.add_edges_from([(src, dst)], retain, **kwargs)

    def add_edges_from(self, ebunch, retain=[], **kwargs):
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

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
        self.timestamp =  time.strftime("%Y%m%d_%H%M%S", time.localtime())

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
