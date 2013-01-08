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

messaging = autonetkit.ank_messaging.AnkMessaging()

#TODO: allow slack in allocations: both for ASN (group level), and for collision domains to allow new nodes to be easily added

try:
    import cPickle as pickle
except ImportError:
    import pickle

def subnet_size(host_count):
    """Returns subnet size"""
    import math
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

    def is_host(self):
        return self.host

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
        import gzip
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
        unallocated_nodes = sorted(unallocated_nodes, key = lambda x: x.get(group_attr))
        for attr_value, items in itertools.groupby(unallocated_nodes, key = lambda x: x.get(group_attr)):
# make subtree for each attr
            items = list(items)
            subgraph = nx.DiGraph()
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

            for level, nodes in nodes_by_level.items():
                level_counts[level] = len(nodes)

            self.add_parent_nodes(subgraph, level_counts)

            # rebuild with parent nodes
            nodes_by_level = defaultdict(list)
            for node in subgraph.nodes():
                prefixlen = subgraph.node[node]['prefixlen']
                nodes_by_level[prefixlen].append(node)

            root_node = self.build_tree(subgraph, level_counts, nodes_by_level)
            subgraphs.append(subgraph)

            subgraph.graph['root'] = root_node
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
        global_ip_block = netaddr.IPNetwork("%s/%s" % (self.root_ip_block, global_prefix_len))
        self.graph = global_graph

# add children of collision domains
        cd_nodes = [n for n in self if n.is_collision_domain()]
        for cd in cd_nodes:
            for edge in sorted(cd.host.edges()):
                #TODO: sort these
                child_id = self.next_node_id
                cd_id = cd.node
                global_graph.add_node(child_id, prefixlen = 32, host = edge)
                global_graph.add_edge(cd_id, child_id) # cd -> neigh (cd is parent)

#TODO: make allocate seperate step
        def allocate(node):
            #children = graph.successors(node)
            children = sorted(node.children())
            prefixlen = node.prefixlen
            subnet = node.subnet.subnet(prefixlen+1)

            if node.is_loopback_group(): # special case of single AS -> root is loopback_group
                #TODO: generalise this rather than repeated code with below
                #node.subnet = subnet.next() # Note: don't break into smaller subnets if single-AS
                iterhosts = node.subnet.iter_hosts() # ensures start at .1 rather than .0
                sub_children = node.children()
                for sub_child in sub_children:
                    sub_child.subnet = iterhosts.next()

                return

            for child in children:
                if child.is_collision_domain():
                    child.subnet = subnet.next()
                    iterhosts = child.subnet.iter_hosts() # ensures start at .1 rather than .0
                    sub_children = child.children()
                    for sub_child in sub_children:
                        sub_child.subnet = iterhosts.next()
                        log.debug( "Allocate sub_child to %s %s" % ( sub_child, sub_child.subnet))
                elif child.is_host():
                    child.subnet = subnet.next()
                elif child.is_loopback_group():
                    child.subnet = subnet.next()
                    iterhosts = child.subnet.iter_hosts() # ensures start at .1 rather than .0
                    sub_children = child.children()
                    for sub_child in sub_children:
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
        edges = [n for n in self if n.is_host() and n.host.src]
        for edge in edges:
            #print "edge subnet", edge.subnet
            edge.host.ip_address = edge.subnet


#TODO: do we need to store loopback groups into advertise addresses?

        #loopback_groups = [n for n in self if n.is_loopback_group()]
        #for loopback_group in loopback_groups:
            #print loopback_group
    
        # don't look at host nodes now - use loopback_groups
        host_tree_nodes = [n for n in self if n.is_host() and n.host.is_l3device]
        #for host_tree_node in host_tree_nodes:
            #print host_tree_node, host_tree_node.subnet
        for host_tree_node in host_tree_nodes:
            host_tree_node.host.loopback = host_tree_node.subnet

        cds = [n for n in self if n.is_collision_domain()]
        for cd in cds:
            cd.host.subnet = cd.subnet

def assign_asn_to_interasn_cds(G_ip):
    G_phy = G_ip.overlay.phy
    for collision_domain in G_ip.nodes("collision_domain"):
        neigh_asn = list(ank_utils.neigh_attr(G_ip, collision_domain, "asn", G_phy)) #asn of neighbors
        if len(set(neigh_asn)) == 1:
            asn = set(neigh_asn).pop() # asn of any neigh, as all same
        else:
            asn = ank_utils.most_frequent(neigh_asn) # allocate cd to asn with most neighbors in it
        collision_domain.asn = asn

    return

def allocate_ips(G_ip):
    log.info("Allocating Host loopback IPs")
    ip_tree = IpTree("10.0.0.0")
    ip_tree.add_nodes(G_ip.nodes("is_l3device"))
    ip_tree.build()
    loopback_tree = ip_tree.json()
   # json.dumps(ip_tree.json(), cls=autonetkit.ank_json.AnkEncoder, indent = 4)
    #body = json.dumps({"ip_allocations": jsontree})
    #messaging.publish_compressed("www", "client", body)
    ip_tree.assign()
    G_ip.data.loopback_blocks = ip_tree.group_allocations()

    log.info("Allocating Collision Domain IPs")

    ip_tree = IpTree("192.168.1.0")
    assign_asn_to_interasn_cds(G_ip)
    ip_tree.add_nodes(G_ip.nodes("collision_domain"))
    ip_tree.build()
    cd_tree = ip_tree.json()
    ip_tree.assign()

    total_tree = {
            'name': "ip",
            'children': 
                [loopback_tree, cd_tree],
                #[loopback_tree],
            }
    jsontree = json.dumps(total_tree, cls=autonetkit.ank_json.AnkEncoder, indent = 4)

    body = json.dumps({"ip_allocations": jsontree})
    messaging.publish_compressed("www", "client", body)

#TODO: need to update with loopbacks if wish to advertise also - or subdivide blocks?
    G_ip.data.infra_blocks = ip_tree.group_allocations()

    #ip_tree.save()
