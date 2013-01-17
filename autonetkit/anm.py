import networkx as nx
import itertools
import pprint
import time
from ank_utils import unwrap_edges, unwrap_nodes
import autonetkit.log as log
import functools
import string

try:
    import cPickle as pickle
except ImportError:
    import pickle

#TODO: add helper functions such as router, ie ank.router(device): return device.overlay.phys.device_type == "router"

#Add plotting abilities, and allow legend attribute to be set: for both color and symbol

# working with views allows us to spin off subgraphs, and work with them the same as a standard overlay

#TODO: move exceptions into the exception class
class AutoNetkitException(Exception):
    pass

class OverlayNotFound(AutoNetkitException):
    def __init__(self, Errors):
        self.Errors = Errors

    def __str__(self):
        return "Overlay %s not found" % self.Errors

class IntegrityException(AutoNetkitException):
    def __init__(self, Errors):
        self.Errors = Errors

    def __str__(self):
        return "Device %s not found in physical graph" % self.Errors

class DeviceNotFoundException(AutoNetkitException):
    def __init__(self, message, Errors):
        Exception.__init__(self, message)
        self.Errors = Errors

    def __str__(self):
        return "Unable to find %s" % self.Errors

class NodeNotFoundException(AutoNetkitException):
    def __init__(self, message, Errors):
        Exception.__init__(self, message)
        self.Errors = Errors

    def __str__(self):
        return "Unable to find %s" % self.Errors

class EdgeNotFound(AutoNetkitException):
    def __init__(self, message, Errors):
        Exception.__init__(self, message)
        self.Errors = Errors

    def __str__(self):
        return "Unable to find %s" % self.Errors

class overlay_node_accessor(object):
    """API to access overlay nodes in ANM"""
    def __init__(self, anm,  node_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'node_id', node_id)

    def __repr__(self):
        #TODO: make this list overlays the node is present in
        return "Overlay graphs: %s" % ", ".join(sorted(self.anm._overlays.keys()))

    def __getattr__(self, overlay_id):
        """Access overlay graph"""
        return overlay_node(self.anm, overlay_id, self.node_id)

class overlay_edge_accessor(object):
    """API to access overlay nodes in ANM"""
#TODO: fix consistency between node_id (id) and edge (overlay edge)
    def __init__(self, anm, edge):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'edge', edge)

    def __repr__(self):
        #TODO: make this list overlays the node is present in
        return "Overlay edge accessor: %s" % self.edge

    def __getattr__(self, overlay_id):
        """Access overlay edge"""
#TODO: check on returning list or single edge if multiple found with same id (eg in G_igp from explode)
        overlay  = overlay_graph(self.anm, overlay_id)
        edge = overlay.edge(self.edge)
        return edge

class overlay_interface(object):
    def __init__(self, anm, overlay_id, node_id, interface_id):
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'node_id', node_id)
        object.__setattr__(self, 'interface_id', interface_id)

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.anm._overlays[self.overlay_id]

    @property
    def _node(self):
        """Return graph the node belongs to"""
        return self._graph.node[self.node_id]
    
    @property
    def _interface(self):
        """Return graph the node belongs to"""
        return self._node["_interfaces"][self.interface_id]


    @property
    def node(self):
        """Returns parent node of this interface"""
        return overlay_node(self.anm, self.overlay_id, self.node_id)

    def __str__(self):
        return "Interface: " + str(self.interface_id)

    def dump(self):
        return str(self._interface.items())

    def __getattr__(self, key):
        """Returns interface property"""
#TODO: make this log to debug on a miss, ie if key not found: do a try/except for KeyError for this
        try:
            return self._interface.get(key)
        except KeyError:
            return

    def get(self, key):
        """For consistency, node.get(key) is neater than getattr(interface, key)"""
        return getattr(self, key)

    def __setattr__(self, key, val):
        """Sets interface property"""
        try:
            self._interface[key] = val
        except KeyError:
            #TODO: check if this is reachable for a dict
            self.set(key, val)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater than setattr(interface, key, value)"""
        return self.__setattr__(key, val)

    def edges(self):
        """Returns all edges from node that have this interface ID
        This is the convention for binding an edge to an interface"""
        valid_edges = [ e for e in self.node.edges() if self.interface_id in e._interfaces]
        return valid_edges

@functools.total_ordering
class overlay_node(object):
    def __init__(self, anm, overlay_id, node_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
#TODO: check node_id is in graph, otherwise return NodeNotFoundException
# should be able to use _graph from here as anm and overlay_id are defined
        object.__setattr__(self, 'node_id', node_id)

#TODO: allow access back up to overlays from this
# eg self.ip.property self.bgp.property etc

    def __hash__(self):
        return hash(self.node_id)

    def __nonzero__(self):
        """Allows for checking if node exists
        """
        try:
            self._graph.node[self.node_id]
            return True
        except KeyError:
            return False

    def __iter__(self):
        return iter(overlay_interface(self.anm, self.overlay_id, self.node_id, interface_id)
                for interface_id in self._interfaces)

    def __getnewargs__(self):
        return ()

    def __getstate__(self):
        """For pickling"""
        return (self.anm, self.overlay_id, self.node_id)

    def __setstate__(self, state):
        # Make self.history = state and last_change and value undefined
        (anm, overlay_id, node_id) = state
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'node_id', node_id)

    def __eq__(self, other):
        try:
            return self.node_id == other.node_id
        except AttributeError:
            return self.node_id == other #TODO: check why comparing against strings - if in overlay graph...

    def __lt__(self, other):
# want [r1, r2, ..., r11, r12, ..., r21, r22] not [r1, r11, r12, r2, r21, r22]
# so need to look at numeric part
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
    def _next_int_id(self):
# returns next free interface ID 
        for int_id in itertools.count(1): # start at 1 as 0 is loopback
            if int_id not in self._interfaces:
                return int_id

    def _add_interface(self, description = None):
        next_id = self._next_int_id
        self._interfaces[next_id] = {
                'description': description,
                }
        return next_id


    @property
    def _interfaces(self):
        return self._graph.node[self.node_id]["_interfaces"]

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.anm._overlays[self.overlay_id]

    @property
    def is_router(self):
        """Either from this graph or the physical graph"""
        return self.device_type == "router" or self.phy.device_type == "router"

    @property
    def is_switch(self):
        return self.device_type == "switch" or self.phy.device_type == "switch"

    @property
    def is_server(self):
        return self.device_type == "server" or self.phy.device_type == "server"

    @property
    def is_l3device(self):
        """Layer 3 devices: router, server, cloud, host
        ie not switch
        """
        return self.is_router or self.is_server

    def __getitem__(self, key):
        return overlay_node(self.anm, key, self.node_id)

#TODO: Add other base device_types

#TODO: check asn handling if devices added directly eg in graph products
    @property
    def asn(self):
        try:
            return self._graph.node[self.node_id]['asn'] # not in this graph
        except KeyError:
            #TODO: catch case of phy graph not existing yet, eg making G_graphics
            return self.anm._overlays['phy'].node[self.node_id]['asn'] #try from phy

    @property
    def id(self):
        return self.node_id

    @property
    def _overlay(self):
        return overlay_graph(self.anm, self.overlay_id)

    def degree(self):
        return self._graph.degree(self.node_id)

    def neighbors(self):
        return self._overlay.neighbors(self)

    @property
    def label(self):
        return self.__repr__()

    @property
    def phy(self):
        """Shortcut back to physical overlay_node
        Same as node.overlay.phy
        ie node.phy.x is same as node.overlay.phy.x
        """
# refer back to the physical node, to access attributes such as name
#TODO: handle case of trying to access phy in phy: loop, can't just return self
        return overlay_node(self.anm, "phy", self.node_id)

    def dump(self):
        return str(self._graph.node[self.node_id])
    
    @property
    def overlay(self):
        """Access node in another overlay graph"""
        return overlay_node_accessor(self.anm, self.node_id)

    def edges(self, *args, **kwargs):
        #TODO: want to add filter for *args and **kwargs here too
        return self._overlay.edges(self, *args, **kwargs)

    def __repr__(self):
        """Try label if set in overlay, otherwise from physical, otherwise node id"""
#TODO: make access direct from phy, and can then do "%s: %s" % (overlay_id, label)
        try:
            return self.anm.node_label(self)
        except KeyError:
            try:
#TODO: shouldn't this be accessing the physical graph?
                return self._graph.node[self.node_id]['label']
            except KeyError:
                return self.node_id # node not in physical graph

    def __getattr__(self, key):
        """Returns node property
        This is useful for accesing attributes passed through from graphml"""
#TODO: make this log to debug on a miss, ie if key not found: do a try/except for KeyError for this
        try:
            return self._graph.node[self.node_id].get(key)
        except KeyError:
            return

    def get(self, key):
        """For consistency, node.get(key) is neater than getattr(node, key)"""
        return getattr(self, key)

    def __setattr__(self, key, val):
        """Sets node property
        This is useful for accesing attributes passed through from graphml"""
        try:
            self._graph.node[self.node_id][key] = val
        except KeyError:
            self._graph.add_node(self.node_id)
            self.set(key, val)

    def set(self, key, val):
        """For consistency, node.set(key, value) is neater than setattr(node, key, value)"""
        return self.__setattr__(key, val)

@functools.total_ordering
class overlay_edge(object):
    """API to access link in network"""
    def __init__(self, anm, overlay_id, src_id, dst_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)

    def __repr__(self):
        return "%s: (%s, %s)" % (self.overlay_id, self.src, self.dst)

    def __getnewargs__(self):
        return ()

    def __getitem__(self, key):
        overlay  = overlay_graph(self.anm, key)
        return overlay.edge(self)

    def __getstate__(self):
        """For pickling"""
        return (self.anm, self.overlay_id, self.src_id, self.dst_id)

    def __lt__(self, other):
        return ((self.src.node_id, self.dst.node_id) < (other.src.node_id, other.dst.node_id))

    def __setstate__(self, state):
        """For pickling"""
        self._overlays = state
        (anm, overlay_id, src_id, dst_id) = state
#TODO: call to self __init__ ???
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)
        object.__setattr__(self, 'src_id', src_id)
        object.__setattr__(self, 'dst_id', dst_id)

    @property
    def src(self):
        return overlay_node(self.anm, self.overlay_id, self.src_id)

    @property
    def dst(self):
        return overlay_node(self.anm, self.overlay_id, self.dst_id)

    def attr_equal(self, *args):
        """Return edges which both src and dst have attributes equal"""
        return all(getattr(self.src, key) == getattr(self.dst, key) for key in args )

    def attr_both(self, *args):
        """Return edges which both src and dst have attributes set"""
        return all((getattr(self.src, key) and getattr(self.dst, key)) for key in args )

    def attr_any(self, *args):
        """Return edges which either src and dst have attributes set"""
        return all((getattr(self.src, key) or getattr(self.dst, key)) for key in args )

    def dump(self):
        return str(self._graph[self.src_id][self.dst_id])

    def __nonzero__(self):
        """Allows for checking if edge exists
        """
        try:
            self._graph[self.src_id][self.dst_id] # edge exists
            return True
        except KeyError:
            return False
        
    def bind_interface(self, node, interface):
        #TODO: need to handle both nodes and node ids
        #TODO: need to handle both interfaces and interface ids
        self._interfaces[node.id] = interface

    @property
    def overlay(self):
        """Access node in another overlay graph"""
        return overlay_edge_accessor(self.anm, self)

    @property
    def _graph(self):
        """Return graph the node belongs to"""
        return self.anm._overlays[self.overlay_id]

    def get(self, key):
        """For consistency, edge.get(key) is neater than getattr(edge, key)"""
        return self.__getattr__(key)

    def set(self, key, val):
        """For consistency, edge.set(key, value) is neater than setattr(edge, key, value)"""
        return self.__setattr__(key, val)

    def __getattr__(self, key):
        """Returns edge property"""
        return self._graph[self.src_id][self.dst_id].get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._graph[self.src_id][self.dst_id][key] = val

class overlay_graph_data(object):
    """API to access link in network"""
    def __init__(self, anm, overlay_id):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)

    def __repr__(self):
        return "Data for (%s, %s)" % (self.anm, self.overlay_id)

    def dump(self):
        print str(self._graph.graph) 

    @property
    def _graph(self):
        #access underlying graph for this overlay_node
        return self.anm._overlays[self.overlay_id]

    def __getattr__(self, key):
        """Returns edge property"""
        return self._graph.graph.get(key)

    def __setattr__(self, key, val):
        """Sets edge property"""
        self._graph.graph[key] = val

class OverlayBase(object):
    """Base class for overlays - overlay graphs, subgraphs, projections, etc"""

    def __init__(self, anm, overlay_id):
        if overlay_id not in anm._overlays:
            raise OverlayNotFound(overlay_id)
        self._anm = anm
        self._overlay_id = overlay_id

    def __repr__(self):
        return self._overlay_id

    @property
    def data(self):
        return overlay_graph_data(self._anm, self._overlay_id)

    def __contains__(self, n):
        return n.node_id in self._graph

    def edge(self, edge_to_find, dst_to_find = None):
        """returns edge in this graph with same src and same edge_id"""
        try:
            if dst_to_find:
                src_id = edge_to_find.node_id
                search_id = dst_to_find.node_id
            else:
                src_id = edge_to_find.src_id
                search_id = edge_to_find.edge_id
        except AttributeError:
            src_id = None
            search_id = edge_to_find
#TODO: if no edge_id then search for src, dst pair

        for src, dst in self._graph.edges_iter(src_id):
            try:
                if self._graph[src][dst]['edge_id'] == search_id:
                    return overlay_edge(self._anm, self._overlay_id, src, dst)
            except KeyError:
                pass # no edge_id for this edge

    def node(self, key):
        """Returns node based on name
        This is currently O(N). Could use a lookup table"""
#TODO: check if node.node_id in graph, if so return wrapped node for this...
# returns node based on name
        try:
            if key.node_id in self._graph:
                return overlay_node(self._anm, self._overlay_id, key.node_id)
        except AttributeError:
            # doesn't have node_id, likely a label string, search based on this label
            for node in self:
                if str(node) == key:
                    return node
            log.warning( "Unable to find node %s in %s " % (key, self))
            return None

#TODO: Allow overlay data to be set/get, ie graph.graph eg for asn subnet allocations

    def degree(self, node):
        return node.degree()

    def neighbors(self, node):
        return iter(overlay_node(self._anm, self._overlay_id, node)
                for node in self._graph.neighbors(node.node_id))

    @property
    def overlay(self):
        """Get to other overlay graphs in functions"""
        return overlay_accessor(self._anm)

    @property
    def name(self):
        return self.__repr__()

    def node_label(self, node):
        return repr(overlay_node(self._anm, self._overlay_id, node))

    def dump(self):
        #TODO: map this to ank functions
        self._anm.dump_graph(self)

    def has_edge(self, edge):
        """Tests if edge in graph"""
#TODO: handle case of user creating edge, eg test tuples and ids directly
        return self._graph.has_edge(edge.src, edge.dst)

    def __iter__(self):
        return iter(overlay_node(self._anm, self._overlay_id, node)
                for node in self._graph)

    def __len__(self):
        return len(self._graph)

    def nodes(self, *args, **kwargs):
        result = self.__iter__()
        if len(args) or len(kwargs):
            result = self.filter(result, *args, **kwargs)
        return result

    def routers(self, *args, **kwargs):
        """Shortcut for nodes(), sets device_type to be router"""
        kwargs['device_type'] = 'router'
        return self.nodes(*args, **kwargs)

    def device(self, key):
        """To access programatically"""
        return overlay_node(self._anm, self._overlay_id, key)

    def groupby(self, attribute, nodes = None):
        """Returns a dictionary sorted by attribute
#TODO: Also want to be able to return list of subgraphs based on groupby, eg per ASN subgraphs
        
        >>> G_in.groupby("asn")
        {u'1': [r1, r2, r3, sw1], u'2': [r4]}
        """
        result={}
    
        if not nodes:
            data = self.nodes()
        else:
            data = nodes
        data = sorted(data, key= lambda x: x.get(attribute))
        for k, g in itertools.groupby(data, key= lambda x: x.get(attribute)):
            result[k] = list(g)

        #TODO: should this return .items() to be consistent with other iterables?
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

    def edges(self, src_nbunch = None, dst_nbunch = None, *args, **kwargs):
# nbunch may be single node
#TODO: Apply edge filters
        if src_nbunch:
            try:
                src_nbunch = src_nbunch.node_id
            except AttributeError:
                src_nbunch = (n.node_id for n in src_nbunch) # only store the id in overlay

        def filter_func(edge):
            return (
                    all(getattr(edge, key) for key in args) and
                    all(getattr(edge, key) == val for key, val in kwargs.items())
                    )

        valid_edges = ( (src, dst) for (src, dst) in self._graph.edges_iter(src_nbunch))
        if dst_nbunch:
            try:
                dst_nbunch = dst_nbunch.node_id
                dst_nbunch = set([dst_nbunch]) # faster membership test than other sequences
            except AttributeError:
                dst_nbunch = (n.node_id for n in dst_nbunch) # only store the id in overlay_edge
                dst_nbunch = set(dst_nbunch) # faster membership test than other sequences

            valid_edges  = ((src, dst) for (src, dst) in valid_edges
                    if dst in dst_nbunch)

        if len(args) or len(kwargs):
            all_edges = iter(overlay_edge(self._anm, self._overlay_id, src, dst)
                    for (src, dst) in valid_edges)
            result =  (edge for edge in all_edges if filter_func(edge))
        else:
            result =  (overlay_edge(self._anm, self._overlay_id, src, dst)
                    for (src, dst) in valid_edges)
        return result

class overlay_subgraph(OverlayBase):
    def __init__(self, anm, overlay_id, graph, name = None):
        super(overlay_subgraph, self).__init__(anm, overlay_id)
        self._graph = graph
        self._subgraph_name = name

    def __repr__(self):
        return self._subgraph_name or "subgraph"

class overlay_graph(OverlayBase):
    """API to interact with an overlay graph in ANM"""
#TODO: provide an strip_id function to turn node tuples back into just ids for the graph

    @property
    def anm(self):
        return self._anm

    @property
    def _graph(self):
        #access underlying graph for this overlay_node
        return self._anm._overlays[self._overlay_id]

    def _replace_graph(self, graph):
        self._anm._overlays[self._overlay_id] = graph

    # these work similar to their nx counterparts: just need to strip the node_id
    def add_nodes_from(self, nbunch, retain=[], update = False, **kwargs):
        """Update won't append data (which could clobber) if node exists"""
        #Can't just append _interfaces or won't work for copying from G_in
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        if not update:
# filter out existing nodes
            nbunch = (n for n in nbunch if n not in self._graph)

        nbunch = list(nbunch);
        node_ids = list(nbunch) # before appending retain data

        if len(retain):
            add_nodes = []
            for n in nbunch:
                data = dict( (key, n.get(key)) for key in retain)
                add_nodes.append( (n.node_id, data) )
            nbunch = add_nodes
        else:
            nbunch = (n.node_id for n in nbunch) # only store the id in overlay

#TODO: need to copy across _interfaces keys

        nbunch = list(nbunch)
        self._graph.add_nodes_from(nbunch, **kwargs)
        self._init_interfaces(node_ids)

    def add_node(self, node, retain=[], **kwargs):
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        try:
            node_id = node.id
        except AttributeError:
            node_id = node # use the string node id

        data = {}
        if len(retain):
            data = dict( (key, node.get(key)) for key in retain)
            kwargs.update(data) # also use the retained data
        self._graph.add_node(node_id, kwargs)
        self._init_interfaces([node_id])

    def _init_interfaces(self, nbunch = None):
        #TODO: make this more efficient by taking in the newly added node ids as a parameter
        if not nbunch:
            nbunch = [n for n in self._graph.nodes()]

        try:
            nbunch = list(unwrap_nodes(nbunch))
        except AttributeError:
            pass # don't need to unwrap

        phy_graph = self._anm._overlays["phy"]
        
        for node in nbunch:
            #TODO: tidy up this hardcoded logic
            try:
                phy_interfaces = phy_graph.node[node]["_interfaces"]
                data = dict( (key, {}) for key in phy_interfaces)
                self._graph.node[node]['_interfaces'] = data
            except KeyError:
# no counterpart in physical graph, initialise
                log.debug("Initialise interfaces for %s in %s" % (node, self._overlay_id))
                self._graph.node[node]['_interfaces'] = {0: {'description': 'loopback'}}


    def allocate_interfaces(self):
        #TODO: take in a list of edges to use to map
        """allocates edges to interfaces"""
#TODO: only allocate if not allocated
        #int_counter = (n for n in itertools.count() if n not in 
        self._init_interfaces()

#TODO: take in nbunch of nodes to allocate for
        ebunch = (e for e in self.edges())
        for edge in ebunch:
            src = edge.src
            dst = edge.dst
            src_int_id = src._add_interface('link to %s' % dst)
            dst_int_id = dst._add_interface('link to %s' % src)
            edge._interfaces = {}
            edge._interfaces[src.id] = src_int_id
            edge._interfaces[dst.id] = dst_int_id

    def remove_node(self, node, **kwargs):
        try:
            node_id = node.node_id
        except AttributeError:
            node_id = node
        self._graph.remove_node(node_id)

    def add_edge(self, src, dst, retain=[], **kwargs):
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list
        self.add_edges_from([(src, dst)], retain, **kwargs)

    def remove_edges_from(self, ebunch):
        #TODO: check if this try/except consumes generator
        try:
            ebunch = unwrap_edges(ebunch)
        except AttributeError:
            pass # don't need to unwrap
        self._graph.remove_edges_from(ebunch)


    def add_edges(self, *args, **kwargs):
        self.add_edges_from(args, kwargs)

    def add_edges_from(self, ebunch, bidirectional = False, retain=[], **kwargs):
        """Add edges. Unlike NetworkX, can only add an edge if both src and dst in graph already.
        If they are not, then they will not be added (silently ignored)

        Bidirectional will add edge in both directions. Useful if going from an undirected graph to a 
        directed, eg G_in to G_bgp
        """
        #TODO: need to test if given a (id, id) or an edge overlay pair... use try/except for speed
#TODO: tidy this logic up, use edge unwrap and 
# data = dict( (key, graph[src][dst][key]) for key in retain)
        try:
            retain.lower()
            retain = [retain] # was a string, put into list
        except AttributeError:
            pass # already a list

        retain.append("edge_id")
        retain.append("_interfaces")
        try:
            if len(retain):
                #TODO: cleanup this logic: will always at least retain edge_id
                add_edges = []
                for e in ebunch:
                    data = dict( (key, e.get(key)) for key in retain)
                    add_edges.append( (e.src.node_id, e.dst.node_id, data) )
                ebunch = add_edges
            else:
                ebunch = [(e.src.node_id, e.dst.node_id, {}) for e in ebunch]
        except AttributeError:
            data = {"_interfaces": {}} #TODO: bind this to a default interface on both
            ebunch = [(src.node_id, dst.node_id, data) for src, dst in ebunch]

        ebunch = [(src, dst, data) for (src, dst, data) in ebunch if src in self._graph and dst in self._graph]
        if bidirectional:
            #TODO: need to filter out the other interface for bi-directional inks
            ebunch += [(dst, src, data) for (src, dst, data) in ebunch if src in self._graph and dst in self._graph]
#TODO: log to debug any filtered out nodes... if if lengths not the same

        #TODO: decide if want to allow nodes to be created when adding edge if not already in graph
        self._graph.add_edges_from(ebunch, **kwargs)

    def update(self, nbunch = None, **kwargs):
        """Sets property defined in kwargs to all nodes in nbunch"""
        if not nbunch:
            nbunch = self.nodes()
        for node in nbunch:
            for key, value in kwargs.items():
                node.set(key, value)

    def update_edges(self, ebunch = None, **kwargs):
        """Sets property defined in kwargs to all edges in ebunch"""
        if not ebunch:
            ebunch = self.edges()
        for edge in ebunch:
            for key, value in kwargs.items():
                edge.set(key, value)

    def subgraph(self, nbunch, name=None):
        nbunch = (n.node_id for n in nbunch) # only store the id in overlay
        return overlay_subgraph(self._anm, self._overlay_id, self._graph.subgraph(nbunch), name)

class overlay_accessor(object):
    """API to access overlay graphs in ANM"""
    def __init__(self, anm):
#Set using this method to bypass __setattr__ 
        object.__setattr__(self, 'anm', anm)

    def __repr__(self):
        return "Available overlay graphs: %s" % ", ".join(sorted(self.anm._overlays.keys()))

    def __getattr__(self, key):
        """Access overlay graph"""
        return overlay_graph(self.anm, key)

    def get(self, key):
        return getattr(self, key)

class AbstractNetworkModel(object):
    def __init__(self):
        self._overlays = {}
        self.add_overlay("phy")

        self.label_seperator = "_"
        self.label_attrs = ['label']
        self._build_node_label()
        self.timestamp =  time.strftime("%Y%m%d_%H%M%S", time.localtime())
        
    def __getnewargs__(self):
        return ()

    def __getstate__(self):
        """For pickling"""
        return (self._overlays, self.label_seperator, self.label_attrs)

    def __setstate__(self, state):
        """For pickling"""
        (overlays, label_seperator, label_attrs) = state
        self._overlays = overlays
        self.label_seperator = label_seperator
        self.label_attrs = label_attrs
        self._build_node_label()

    def save(self):
        import ank_json
        import os
        import gzip
        archive_dir = os.path.join("versions", "anm")
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

        data = ank_json.jsonify_anm(self)
#TODO: should this use the ank_json.jsonify_nidb() ?
        json_file = "anm_%s.json.gz" % self.timestamp
        json_path = os.path.join(archive_dir, json_file)
        log.debug("Saving to %s" % json_path)
        with gzip.open(json_path, "wb") as json_fh:
            json_fh.write(data)

    def restore_latest(self, directory = None):
        import os
        import glob
        if not directory:
        #TODO: make directory loaded from config
            directory = os.path.join("versions", "anm")

        glob_dir = os.path.join(directory, "*.json.gz")
        pickle_files = glob.glob(glob_dir)
        pickle_files = sorted(pickle_files)
        try:
            latest_file = pickle_files[-1]
        except IndexError:
# No files loaded
            log.warning("No previous ANM saved. Please compile new ANM")
            return
        self.restore(latest_file)

    def restore(self, pickle_file):
        import json
        import gzip
        import ank_json
        log.debug("Restoring %s" % pickle_file)
        with gzip.open(pickle_file, "r") as fh:
            data = json.load(fh) 
            for overlay_id, graph_data in data.items():
                self._overlays[overlay_id] = ank_json.ank_json_loads(graph_data)

    @property
    def _phy(self):
        return overlay_graph(self, "phy")

    def add_overlay(self, name, nodes = None, graph = None, directed=False, multi_edge=False, retain = None ):
        """Adds overlay graph of name name"""
#TODO: allow retain to be specified and passed through to the add_nodes_from call
        if graph:
            if not directed and graph.is_directed():
                log.info("Converting graph %s to undirected" %  name)
                graph = nx.Graph(graph)

        elif directed:
            if multi_edge:
                graph = nx.MultiDiGraph()
            else:
                graph = nx.DiGraph()
        else:
            if multi_edge:
                graph = nx.MultiGraph()
            else:
                graph = nx.Graph()

        self._overlays[name] = graph
        overlay =  overlay_graph(self, name)
        overlay.allocate_interfaces()
        if nodes:
            retain = retain or [] # default is an empty list
            overlay.add_nodes_from(nodes, retain)
        return overlay

    @property
    def overlay(self):
        return overlay_accessor(self)

#TODO: make this a property
    def overlays(self):
        return self._overlays.keys()

    def devices(self, *args, **kwargs):
        return self._phy.filter(*args, **kwargs)

    def __getitem__(self, key):
        return overlay_graph(self, key)

    def node_label(self, node):
        """Returns node label from physical graph"""
        return self.default_node_label(node)

    def _build_node_label(self):
        def custom_label(node):
            return self.label_seperator.join(str(self._overlays['phy'].node[node.node_id].get(val)) 
                    for val in self.label_attrs
                    if self._overlays['phy'].node[node.node_id].get(val) != None)

        self.node_label = custom_label

    def set_node_label(self, seperator, label_attrs):
        try:
            label_attrs.lower()
            label_attrs = [label_attrs] # was a string, put into list
        except AttributeError:
            pass # already a list

        self.label_seperator = seperator
        self.label_attrs = label_attrs


    #TODO: move this out into debug module
    def dump_graph(self, graph):
        print "----Graph %s----" % graph
        print "Graph"
        print self.dump_graph_data(graph)
        print "Nodes"
        print self.dump_nodes(graph)
        print "Edges"
        print self.dump_edges(graph)

    def dump_graph_data(self, graph):
        debug_data = dict( (key, val)
                for key, val in sorted(graph._graph.graph.items()))
        return pprint.pformat(debug_data)

    def dump_nodes(self, graph):
        debug_data = dict( (graph.node_label(node), data)
                for node, data in (graph._graph.nodes(data=True)))
        return pprint.pformat(debug_data)

    def dump_edges(self, graph):
        debug_data = dict( ((graph.node_label(src), graph.node_label(dst)), data
            ) for src, dst, data in (graph._graph.edges(data=True)))
        return pprint.pformat(debug_data)



"""TODO: allow graphs to be frozen for integrity, 
eg load input, freeze, 
and once done with overlays freeze them before nidb
"""


