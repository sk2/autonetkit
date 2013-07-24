import time
import json
import itertools
import math
import autonetkit.ank as ank_utils
import autonetkit.log as log
import autonetkit.ank_json
import networkx as nx
from collections import defaultdict
import netaddr
import functools
import autonetkit.ank_messaging

#TODO: allow slack in allocations: both for ASN (group level), and for collision domains to allow new nodes to be easily added

try:
    import cPickle as pickle
except ImportError:
    import pickle

def subnet_size(host_count):
    """Returns subnet size"""
    host_count += 2 # network and broadcast
    return int(math.ceil(math.log(host_count, 2)))

@functools.total_ordering
class TreeNode(object):
    def __init__(self, graph, node):
        object.__setattr__(self, 'graph', graph)
        object.__setattr__(self, 'node', node)

#TODO: make thise fixed attributes, as only certain number needed here
    def __getattr__(self, attr):
        return self.graph.node[self.node].get(attr)

    def __setattr__(self, key, val):
        self.graph.node[self.node][key] = val

    def __lt__(self, other):
        if self.host and other.host:
            return self.host < other.host
        return self.node < other.node

#TODO: restore function that truncated subnets

    def __repr__(self):
        if self.host:
            return "%s %s" % (self.subnet, self.host)
        if self.loopback_group:
            return "Lo Gr %s: %s" % (self.group_attr, self.subnet)
        if self.group_attr:
            return "%s: %s" % (self.group_attr, self.subnet)
        if self.subnet:
            return "%s" % self.subnet
        return "TreeNode: %s" % self.node 

    def is_collision_domain(self):
        return (self.host and self.host.collision_domain)

    def is_loopback_group(self):
        return self.loopback_group

    def is_interface(self):
        return isinstance(self.host, autonetkit.anm.overlay_interface)

    def is_host(self):
        return bool(self.host)

    def children(self):
        return [TreeNode(self.graph, child) for child in self.graph.successors(self.node)]

class IpTree(object):
    def __init__(self, root_ip_block):
        self.unallocated_nodes = []
        self.graph = nx.DiGraph()
        self.root_node = None
        self.timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
#taken_nodes -> these are nodes manually specified, eg in graphml
        self.node_id_counter = (i for i in itertools.count(0) if i not in self.graph)
        self.root_ip_block = root_ip_block

    def __len__(self):
        return len(self.graph)

    def __iter__(self):
        return iter(TreeNode(self.graph, node) for node in self.graph)

    @property
    def next_node_id(self):
        return self.node_id_counter.next()

    def add_parent_nodes(self, subgraph, level_counts):
        for level in range(32, 0, -1):
            try:
                current_count = float(level_counts[level]) # float so do floating point division
            except KeyError:
                continue # key not present - likely higher up tree
            parent_count = int(math.ceil(current_count/2))
            parent_level = level - 1
            level_counts[parent_level] += parent_count
            subgraph.add_nodes_from((self.next_node_id, {'prefixlen': parent_level}) for n in range(parent_count))

            if level_counts[parent_level] == 1:
                if parent_level == min(level_counts.keys()):
                    children = [n for n in subgraph if subgraph.node[n]['prefixlen'] == parent_level + 1]
                    if all('host' in subgraph.node[n] for n in children):
                        subgraph.add_node(self.next_node_id, prefixlen = parent_level - 1)

                    break # Reached top of tree

    def build_tree(self, subgraph, level_counts, nodes_by_level):
        smallest_prefix = min(level_counts.keys())
        for prefixlen in range(smallest_prefix, 32):
            #TODO: fix sorting here
            unallocated_children = set(nodes_by_level[prefixlen + 1])
            for node in sorted(nodes_by_level[prefixlen]):
                is_not_subnet = not ("host" in subgraph.node[node] or "group_attr" in subgraph.node[node])
                if is_not_subnet:
                    child_a = unallocated_children.pop()
                    subgraph.add_edge(node, child_a)
                    try:
                        child_b = unallocated_children.pop()
                        subgraph.add_edge(node, child_b)
                    except KeyError:
                        pass # single child, just attach

        root_node = nodes_by_level[smallest_prefix][0]
        return root_node

    def save(self):
        import os
        archive_dir = os.path.join("versions", "ip")
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

        self.graph.graph['timestamp'] = self.timestamp
        data = autonetkit.ank_json.ank_json_dumps(self.graph)
#TODO: should this use the ank_json.jsonify_nidb() ?
        json_file = "ip_%s.json.gz" % self.timestamp
        json_path = os.path.join(archive_dir, json_file)
        log.debug("Saving to %s" % json_path)
        #with gzip.open(json_path, "wb") as json_fh:
        with open(json_path, "wb") as json_fh:
            json_fh.write(data)

    def build(self, group_attr = 'asn'):
        """Builds tree from unallocated_nodes,
        groupby is the attribute to build subtrees from"""
        subgraphs = []

# if network final octet is .0 eg 10.0.0.0 or 192.168.0.0, then add extra "dummy" node, so don't have a loopback of 10.0.0.0
# Change strategy: if just hosts (ie loopbacks), then allocate as a large collision domain
        if not len(self.unallocated_nodes):
# no nodes to allocate - eg could be no collision domains
            return

        unallocated_nodes = self.unallocated_nodes
        key_func  = lambda x: x.get(group_attr)
        if all((isinstance(item, autonetkit.anm.overlay_interface) and item.is_loopback)
                for item in unallocated_nodes):
            key_func  = lambda x: x.node.get(group_attr) # interface, map key function to be the interface's node

        unallocated_nodes = sorted(unallocated_nodes, key = key_func)
        groupings = itertools.groupby(unallocated_nodes, key = key_func)
        for attr_value, items in groupings:
# make subtree for each attr
            items = sorted(list(items))
            subgraph = nx.DiGraph()

            if all(isinstance(item, autonetkit.anm.overlay_interface) for item in items):
                # interface 
                if all(item.is_loopback for item in items):
                    parent_id = self.next_node_id
                    prefixlen = 32 - subnet_size(len(items)) # group all loopbacks into single subnet
                    subgraph.add_node(parent_id, prefixlen = prefixlen, loopback_group = True)
                    for item in items:
                    #subgraph.add_edge(node, child_a)
                        item_id = self.next_node_id
                        subgraph.add_node(item_id, prefixlen = 32, host = item)
                        subgraph.add_edge(parent_id, item_id)

                    root_node = parent_id
                    subgraphs.append(subgraph)
                    subgraph.graph['root'] = root_node
                    subgraph.node[root_node]['group_attr'] = attr_value
                    continue # finished for loopbacks, continue only for collision domains

            if all(item.is_l3device for item in items): 
                # Note: only l3 devices are added for loopbacks: cds allocate to edges not devices (for now) - will be fixed when move to proper interface model 
                parent_id = self.next_node_id
                prefixlen = 32 - subnet_size(len(items)) # group all loopbacks into single subnet
                subgraph.add_node(parent_id, prefixlen = prefixlen, loopback_group = True)
                for item in items:
                #subgraph.add_edge(node, child_a)
                    item_id = self.next_node_id
                    subgraph.add_node(item_id, prefixlen = 32, host = item)
                    subgraph.add_edge(parent_id, item_id)

                root_node = parent_id
                subgraphs.append(subgraph)
                subgraph.graph['root'] = root_node
                subgraph.node[root_node]['group_attr'] = attr_value
                continue # finished for loopbacks, continue only for collision domains

            for item in items:
                if item.collision_domain:
                    subgraph.add_node(self.next_node_id, prefixlen = 32 - subnet_size(item.degree()), host = item)
                if item.is_l3device:
                    subgraph.add_node(self.next_node_id, prefixlen = 32, host = item)

            # now group by levels
            level_counts = defaultdict(int)

            nodes_by_level = defaultdict(list)
            for node in subgraph.nodes():
                prefixlen = subgraph.node[node]['prefixlen']
                nodes_by_level[prefixlen].append(node)

            log.debug("Building IP subtree for %s %s" % (group_attr, attr_value))

            for level, nodes in nodes_by_level.items():
                level_counts[level] = len(nodes)

            self.add_parent_nodes(subgraph, level_counts)
# test if min_level node is bound, if so then add a parent, so root for AS isn't a cd
            min_level = min(level_counts)
            min_level_nodes = [n for n in subgraph if subgraph.node[n]['prefixlen'] == min_level]
            # test if bound
            if len(min_level_nodes) == 2:
                subgraph.add_node(self.next_node_id, {'prefixlen': min_level - 2})
                subgraph.add_node(self.next_node_id, {'prefixlen': min_level - 2})
                subgraph.add_node(self.next_node_id, {'prefixlen': min_level - 1})
            if len(min_level_nodes) == 1:
                subgraph.add_node(self.next_node_id, {'prefixlen': min_level - 1})

            # rebuild with parent nodes
            nodes_by_level = defaultdict(list)
            for node in subgraph.nodes():
                prefixlen = subgraph.node[node]['prefixlen']
                nodes_by_level[prefixlen].append(node)

            root_node = self.build_tree(subgraph, level_counts, nodes_by_level)
            subgraphs.append(subgraph)

            subgraph.graph['root'] = root_node
#FOrce to be a /16 block
#TODO: document this
            subgraph.node[root_node]['prefixlen']  = 16
            subgraph.node[root_node]['group_attr'] = attr_value

        global_graph = nx.DiGraph()
        subgraphs = sorted(subgraphs, key = lambda x: subgraph.node[subgraph.graph['root']]['group_attr'])
        root_nodes = [subgraph.graph['root'] for subgraph in subgraphs]
        root_nodes = []
        for subgraph in subgraphs:
            root_node = subgraph.graph['root']
            root_nodes.append(root_node)
            global_graph.add_node(root_node, subgraph.node[root_node])

        nodes_by_level = defaultdict(list)
        for node in root_nodes:
            prefixlen = global_graph.node[node]['prefixlen']
            nodes_by_level[prefixlen].append(node)

        level_counts = defaultdict(int)
        for level, nodes in nodes_by_level.items():
            level_counts[level] = len(nodes)

        self.add_parent_nodes(global_graph, level_counts)

# rebuild nodes by level
#TODO: make this a function
        nodes_by_level = defaultdict(list)
        for node in global_graph:
            prefixlen = global_graph.node[node]['prefixlen']
            nodes_by_level[prefixlen].append(node)

        global_root = self.build_tree(global_graph, level_counts, nodes_by_level)
        global_root = TreeNode(global_graph, global_root)

        for subgraph in subgraphs:
            global_graph = nx.compose(global_graph, subgraph)

        # now allocate the IPs
        global_prefix_len = global_root.prefixlen
        #TODO: try/catch if the block is too small for prefix
        global_ip_block = self.root_ip_block.subnet(global_prefix_len).next()
        self.graph = global_graph

# add children of collision domains
        cd_nodes = [n for n in self if n.is_collision_domain()]
        for cd in cd_nodes:
            for edge in sorted(cd.host.edges()):
                #TODO: sort these
                child_id = self.next_node_id
                cd_id = cd.node
                global_graph.add_node(child_id, prefixlen = 32, host = edge.dst_int)
                global_graph.add_edge(cd_id, child_id) # cd -> neigh (cd is parent)

#TODO: make allocate seperate step
        def allocate(node):
            #children = graph.successors(node)
            children = sorted(node.children())
            prefixlen = node.prefixlen + 1

            # workaround for clobbering attr subgraph root node with /16 if was a /28 
            """
            child_prefixlen = {c.prefixlen for c in children}.pop()
            if (prefixlen) != child_prefixlen:
                prefixlen = child_prefixlen
            """

            subnet = node.subnet.subnet(prefixlen)

# handle case where children subnet 
            if node.is_loopback_group() or node.is_collision_domain(): # special case of single AS -> root is loopback_group
                #TODO: generalise this rather than repeated code with below
                #node.subnet = subnet.next() # Note: don't break into smaller subnets if single-AS
                iterhosts = node.subnet.iter_hosts() # ensures start at .1 rather than .0
                sub_children = node.children()
                for sub_child in sub_children:
                    #TODO: tidy up this allocation to always record the subnet
                    if sub_child.is_interface() and sub_child.host.is_loopback:
                        if sub_child.host.is_loopback_zero:   
                            # loopback zero, just store the ip address
                            sub_child.ip_address = iterhosts.next()
                        else:
                            # secondary loopback
                            sub_child.ip_address = iterhosts.next()
                            sub_child.subnet = node.subnet
                    elif sub_child.is_interface() and sub_child.host.is_physical:
                        # physical interface
                        sub_child.ip_address = iterhosts.next()
                        sub_child.subnet = node.subnet
                    else:
                        sub_child.subnet = iterhosts.next()

                return

            for child in children:
                # traverse the tree
                if child.is_collision_domain():
                    subnet = subnet.next()
                    child.subnet = subnet
                    iterhosts = child.subnet.iter_hosts() # ensures start at .1 rather than .0
                    sub_children = child.children()
                    for sub_child in sub_children:
                        if sub_child.is_interface():
                            interface = sub_child.host
                            if interface.is_physical:
                                # physical interface
                                sub_child.ip_address = iterhosts.next()
                                sub_child.subnet = subnet 
                            elif interface.is_loopback and not interface.is_loopback_zero:
                                # secondary loopback interface
                                sub_child.ip_address = iterhosts.next()
                                sub_child.subnet = subnet 
                        else:
                            sub_child.subnet = iterhosts.next()

                        log.debug( "Allocate sub_child to %s %s" % ( sub_child, sub_child.subnet))
                elif child.is_host():
                    child.subnet = subnet.next()
                elif child.is_loopback_group():
                    child.subnet = subnet.next()
                    iterhosts = child.subnet.iter_hosts() # ensures start at .1 rather than .0
                    sub_children = child.children()
                    for sub_child in sub_children:
                        if sub_child.is_interface() and not sub_child.host.is_loopback_zero:
                           # secondary loopback
                           sub_child.ip_address = iterhosts.next()
                           sub_child.subnet = child.subnet 
                        else:
                            sub_child.subnet = iterhosts.next()
                else:
                    child.subnet = subnet.next()
                    allocate(child) # continue down the tree

        global_root.subnet = global_ip_block
#TODO: fix this workaround where referring to the wrong graph
        global_root_id = global_root.node
        global_root = TreeNode(global_graph, global_root_id)
        allocate(global_root)

# check for parentless nodes

        self.graph = global_graph
        self.root_node = global_root

    def group_allocations(self):
        allocs = {}
        for node in self:
            if node.group_attr:
                #TODO: Also need to store the type
                allocs[node.group_attr] = [node.subnet]

        return allocs

    def add_nodes(self, nodes):
        self.unallocated_nodes += list(nodes)

    def walk(self):
        def list_successors(node):
            successors = self.graph.successors(node)
            if successors:
                children = [list_successors(n) for n in successors]
                return {node: children}
            return node

        return list_successors(self.root_node)

    def json(self):
        def list_successors(node):
            children = node.children()
            if children:
                children = [list_successors(n) for n in children]
                return {"name": node,
                        "subnet": node.subnet,
                        "children": children}
            return {"name": node, "subnet": node.subnet}

        if not self.root_node:
            log.debug("No root node set")
            return {"name": str(self.root_ip_block),
                    "subnet": str(self.root_ip_block),
                    "children": []}
            return
        return list_successors(self.root_node)

    
    def assign(self):
# assigns allocated addresses back to hosts
        # don't look at host nodes now - use loopback_groups
        host_tree_nodes = [n for n in self if n.is_host() and n.host.is_l3device]
        #for host_tree_node in host_tree_nodes:
            #print host_tree_node, host_tree_node.subnet
        for host_tree_node in host_tree_nodes:
            host_tree_node.host.loopback = host_tree_node.subnet

        cds = [n for n in self if n.is_collision_domain()]
        for cd in cds:
            cd.host.subnet = cd.subnet

        interfaces = [n for n in self if n.is_interface()]
        for n in interfaces:
            interface = n.host
            if interface.is_loopback and interface.is_loopback_zero:
                # primary loopback
                interface.loopback = n.ip_address
            elif interface.is_loopback and not interface.is_loopback_zero:
                # secondary loopback
                interface.loopback = n.ip_address
                interface.subnet = n.subnet
            elif interface.is_physical:
                interface.ip_address = n.ip_address
                interface.subnet = n.subnet

def assign_asn_to_interasn_cds(g_ip, address_block = None):
    G_phy = g_ip.overlay("phy")
    for collision_domain in g_ip.nodes("collision_domain"):
        neigh_asn = list(ank_utils.neigh_attr(g_ip, collision_domain, "asn", G_phy)) #asn of neighbors
        if len(set(neigh_asn)) == 1:
            asn = set(neigh_asn).pop() # asn of any neigh, as all same
        else:
            asn = ank_utils.most_frequent(neigh_asn) # allocate cd to asn with most neighbors in it
        collision_domain.asn = asn

    return

def allocate_infra(g_ip, address_block = None):
    if not address_block:
        address_block = netaddr.IPNetwork("10.0.0.0/8")
    log.info("Allocating v4 Infrastructure IPs")
    ip_tree = IpTree(address_block)
    assign_asn_to_interasn_cds(g_ip)
    ip_tree.add_nodes(g_ip.nodes("collision_domain"))
    ip_tree.build()
    #cd_tree = ip_tree.json()
    ip_tree.assign()

    g_ip.data.infra_blocks = ip_tree.group_allocations()

    #total_tree = { 'name': "ip", 'children': [cd_tree], }
    #jsontree = json.dumps(total_tree, cls=autonetkit.ank_json.AnkEncoder, indent = 4)
    g_ip.data.infra_blocks = ip_tree.group_allocations()

#TODO: apply directly here

def allocate_loopbacks(g_ip, address_block = None):
    if not address_block:
        address_block = netaddr.IPNetwork("192.168.0.0/22")
    log.info("Allocating v4 Primary Host loopback IPs")
    ip_tree = IpTree(address_block)
    ip_tree.add_nodes(g_ip.nodes("is_l3device"))
    ip_tree.build()
    #loopback_tree = ip_tree.json()
    ip_tree.assign()
    g_ip.data.loopback_blocks = ip_tree.group_allocations()

def allocate_vrf_loopbacks(g_ip, address_block = None):
    if not address_block:
        address_block = netaddr.IPNetwork("172.16.0.0/24")

    secondary_loopbacks = [i for n in g_ip.nodes()
        for i in n.loopback_interfaces
        if not i.is_loopback_zero
        ]

    if not len(secondary_loopbacks):
            return # nothing to set
    log.info("Allocating v4 Secondary Host loopback IPs")
    ip_tree = IpTree(address_block)


    vrf_loopbacks = [i for i in secondary_loopbacks
            if i['vrf'].vrf_name]

    ip_tree.add_nodes(vrf_loopbacks)


    ip_tree.build()
    #secondary_loopback_tree = ip_tree.json()
    ip_tree.assign()
    #TODO: store vrf block to g_ip.data
