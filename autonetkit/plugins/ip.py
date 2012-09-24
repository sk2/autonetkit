import time
from collections import defaultdict
import json
import itertools
import pprint
import math
import os
import autonetkit.ank as ank_utils
import autonetkit.log as log
import autonetkit.ank_pika
import autonetkit.ank_json
import networkx as nx
from collections import defaultdict
import netaddr

settings = autonetkit.config.settings
rabbitmq_server = settings['Rabbitmq']['server']
pika_channel = autonetkit.ank_pika.AnkPika(rabbitmq_server)


try:
    import cPickle as pickle
except ImportError:
    import pickle

def subnet_size(host_count):
    """Returns subnet size"""
    import math
    host_count += 2 # network and broadcast
    return int(math.ceil(math.log(host_count, 2)))

class Tree:
    def __init__(self, root_node, asn):
        self.timestamp =  time.strftime("%Y%m%d_%H%M%S", time.localtime())
        self.root_node = root_node
        self.asn = asn

    def __getstate__(self):
        """For pickling"""
        return (self.timestamp, self.root_node, self.asn)

    def __setstate__(self, state):
        """For pickling"""
        (timestamp, root_node, asn) = state
        self.timestamp = timestamp
        self.root_node = root_node
        self.asn = asn

    def save(self):
        import autonetkit.ank_json
        import gzip
        archive_dir = os.path.join("versions", "ip")
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

#TODO: should this use the ank_json.jsonify_nidb() ?
        json_file = "ip_as%s_%s.json.gz" % (self.asn, self.timestamp)
        json_path = os.path.join(archive_dir, json_file)
        log.debug("Saving to %s" % json_path)
        data = self._json_element(self.root_node)
        data = json.dumps(data, cls=autonetkit.ank_json.AnkEncoder, indent = 4)
        with gzip.open(json_path, "wb") as json_fh:
            json_fh.write(data)

    def __str__(self):
        print self.walk_tree(self.root_node)

    def dump(self):
        print self.walk_tree(self.root_node)

    def json(self):
        return json.dumps(self._json_element(self.root_node), indent=4)

    def _json_element(self, node):
        #TODO: need to case IP addresses to string for JSON
        nodes = []
        if node.left:
            nodes.append(self._json_element(node.left))
        if node.right:
            nodes.append(self._json_element(node.right))
        if nodes:
            return {
                    "subnet": str(node),
                    "children": nodes,
                }

        return {"subnet": str(node)}


    def walk_tree(self, node):
        #TODO: combine this with JSON and printing
        if node.left:
            walk_tree(node.left)
        print node
        if node.right:
            walk_tree(node.right)

class TreeNode:
    """Adapted from http://stackoverflow.com/questions/2078669"""
    def __init__(self,left=None,right=None, cd = None):
        self.left=left
        self.right=right
        self.subnet = None
        self.cd = cd

    @property
    def leaf(self):
        """If this node has any children"""
        if not self.left and not self.right:
            return True
        return False

    def __repr__(self):
        if self.cd:
            return '(%s %s)' % ( self.subnet, self.cd)

        return str(self.subnet)

def allocate_to_tree_node(node):
    node_subnet = node.subnet
    #print "node", node, "has subnet", node_subnet
# divide into two
    child_subnets = node_subnet.subnet(node_subnet.prefixlen+1)
    if node.left:
        node.left.subnet = child_subnets.next()
        allocate_to_tree_node(node.left)
    if node.right:
        node.right.subnet = child_subnets.next()
        allocate_to_tree_node(node.right)

def walk_tree(node):
    if node.left:
        walk_tree(node.left)
    print node
    if node.right:
        walk_tree(node.right)

# need to be able to save and restore tree

def allocate_ips_to_cds(node):
    if node.left:
        allocate_ips_to_cds(node.left)
    if node.right:
        allocate_ips_to_cds(node.right)

    if node.cd:
        #print "node", node, "has cd", node.cd
        try:
            node.cd.subnet = node.subnet
        except AttributeError:
            if node.cd == "loopback":
                pass # expected, this is the loopback placeholder, handled seperately
            else:
                raise # something else went wrong


class TreeNode(object):
    def __init__(self, prefixlen, host = None):
        self.subnet = None
        self.prefixlen = prefixlen
        self.host = host
        self.group_attr = None

    def __repr__(self):
        if self.subnet and self.host:
            return "%s, %s" % (self.subnet.network, self.host)
        if self.subnet and self.group_attr:
            return "%s, %s" % (self.subnet, self.group_attr)
        if self.host:
            return "%s" % self.host
        if self.subnet:
            return "%s" % self.formatted_subnet
        return "/%s" % self.prefixlen

    @property
    def formatted_subnet(self):
        prefixlen = self.subnet.prefixlen
        print prefixlen
        octets = str(self.subnet).split(".")
        print octets
        if prefixlen > 24:
            return octets[3]
        elif prefixlen > 16:
            return ".".join([octets[2], octets[3]])
        elif prefixlen > 8:
            return ".".join([octets[1], octets[2], octets[3]])


    def is_subnet(self):
        return not (self.host or self.group_attr) # if no host node, then is a subnet

    def is_host(self):
        return self.host


def add_parent_nodes(subgraph, level_counts):
    for level in range(32, 0, -1):
        try:
            current_count = float(level_counts[level]) # float so do floating point division
        except KeyError:
            continue # key not present - likely higher up tree
        parent_count = int(math.ceil(current_count/2))
# and add this many to the graph for allocation
        parent_level = level - 1
        #print "level", level, "parent", level_counts[parent_level], "add", parent_count
        level_counts[parent_level] += parent_count
        #level_counts[parent_level] += 
# and add this many to graph
        subgraph.add_nodes_from(TreeNode(prefixlen = parent_level) for n in range(parent_count))

        if level_counts[parent_level] == 1:
# only one node at parent
            if parent_level == min(level_counts.keys()):
                break


def build_tree(subgraph, level_counts, nodes_by_level):
    smallest_prefix = min(level_counts.keys())
    for prefixlen in range(smallest_prefix, 32):
        unallocated_children = set(nodes_by_level[prefixlen + 1])
#TODO: make list and sort
        for node in sorted(nodes_by_level[prefixlen]):
            if node.is_subnet():
                child_a = unallocated_children.pop()
                subgraph.add_edge(node, child_a)
                try:
                    child_b = unallocated_children.pop()
                    subgraph.add_edge(node, child_b)
                except KeyError:
                    pass # single child, just attach

    root_node = nodes_by_level[smallest_prefix][0]
    return root_node

class IpTree(object):
    def __init__(self):
        self.unallocated_nodes = []
        self.graph = nx.DiGraph()
        self.root_node = None
#taken_nodes -> these are nodes manually specified, eg in graphml

    def build(self, group_attr = 'asn'):
        """Builds tree from unallocated_nodes,
        groupby is the attribute to build subtrees from"""
        self.graph.add_edges_from([(1,2), (1,3), (2,4), (2,5), (3,6), (3,7), (4,8), (4,9)])
        self.graph.add_edges_from([(4,10), (4,11)])
        #self.graph.add_edges_from([(1,2), (1,3), (2,4), (2,5), (3,6), (3,7), (4,8)])
        self.root_node = 1

        subgraphs = []

        unallocated_nodes = self.unallocated_nodes
        unallocated_nodes = sorted(unallocated_nodes, key = lambda x: x.get(group_attr))
        for attr_value, items in itertools.groupby(unallocated_nodes, key = lambda x: x.get(group_attr)):
# make subtree for each attr
            print group_attr, "is", attr_value
            items = list(items)
            subgraph = nx.DiGraph()
            for item in items:
                if item.collision_domain:
                    subgraph.add_node(TreeNode(prefixlen = 32 - subnet_size(item.degree()), host = item))
                if item.is_l3device:
                    subgraph.add_node(TreeNode(prefixlen = 32, host = item))

            # now group by levels
            level_counts = defaultdict(int)

            nodes_by_level = sorted(subgraph.nodes(), key = lambda x: x.prefixlen)
            for level, items in itertools.groupby(nodes_by_level, key = lambda x: x.prefixlen):
                level_counts[level] = len(list(items))

            #print level_counts
            add_parent_nodes(subgraph, level_counts)

            nodes_by_level = {}
            nodes = sorted(subgraph.nodes(), key = lambda x: x.prefixlen)
            for level, items in itertools.groupby(nodes, key = lambda x: x.prefixlen):
                nodes_by_level[level] = list(items)
            
            #pprint.pprint(nodes_by_level)
            root_node = build_tree(subgraph, level_counts, nodes_by_level)

# now build the tree
            #print level_counts
            #pprint.pprint( nodes_by_level)

            subgraphs.append(subgraph)

            subgraph.graph['root'] = root_node
            root_node.group_attr = attr_value

            # now fit nodes to tree


        global_root = TreeNode(prefixlen = 8)
    # now attach subgraphs to main graph
# join subgraphs


        global_graph = nx.DiGraph()
        subgraphs = sorted(subgraphs, key = lambda x: subgraph.graph['root'].group_attr)
        root_nodes = [subgraph.graph['root'] for subgraph in subgraphs]
        global_graph.add_nodes_from(root_nodes)

        nodes_by_level = defaultdict(list)
        for node in root_nodes:
            nodes_by_level[node.prefixlen].append(node)

        level_counts = defaultdict(int)
        for level, nodes in nodes_by_level.items():
            level_counts[level] = len(nodes)

        add_parent_nodes(global_graph, level_counts)

# rebuild nodes by level
#TODO: make this a function
        for node in global_graph:
            nodes_by_level[node.prefixlen].append(node)

        global_root = build_tree(global_graph, level_counts, nodes_by_level)

        for subgraph in subgraphs:
            global_graph = nx.compose(global_graph, subgraph)

        # now allocate the IPs
        global_ip_block = netaddr.IPNetwork("192.168.0.0/%s" %global_root.prefixlen)
        print global_ip_block

        def allocate(graph, node):
            children = graph.successors(node)
            prefixlen = node.prefixlen
            subnet = node.subnet.subnet(prefixlen+1)
            for child in children:
                child.subnet = subnet.next()
                if not child.is_host():
                    print "allocate to child", child
                    allocate(graph, child)
                else:
                    #print "dont allocate to child", child
                    pass

        global_root.subnet = global_ip_block
        allocate(global_graph, global_root)


#TODO: Store the IP allocations based on the groupattrs


        self.graph = global_graph
        self.root_node = global_root




        #self.graph = subgraph


# now build tree
#TODO: make this work if loading an already existing tree


            #pprint.pprint( subgraph.nodes(data=True))

# organise by prefixlengths to allocate parent nodes


#if collision domain, then add the interfaces connected to it
# if node, then keep it (loopback)

    def add_nodes(self, nodes):
        self.unallocated_nodes += list(nodes)

    def walk(self):
        #print "walk"
        #print nx.dfs_tree(self.graph, self.root_node)
        #print (nx.dfs_successors(self.graph, self.root_node))
        #return
        def list_successors(node):
            successors = self.graph.successors(node)
            if successors:
                children = [list_successors(n) for n in successors]
                return {node: children}
            return node

        return list_successors(self.root_node)


    def json(self):
        def list_successors(node):
            successors = self.graph.successors(node)
            if successors:
                children = [list_successors(n) for n in successors]
                return {"name": node,
                        "children": children}
            return {"name": node}

        return list_successors(self.root_node)

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
    ip_tree = IpTree()

    ip_tree.add_nodes(G_ip.nodes("is_l3device"))
    assign_asn_to_interasn_cds(G_ip)

    ip_tree.add_nodes(G_ip.nodes("collision_domain"))

    ip_tree.build()
    jsontree = json.dumps(ip_tree.json(), cls=autonetkit.ank_json.AnkEncoder, indent = 4)
    #print jsontree
    #print "walk", ip_tree.walk()
    

    body = json.dumps({"ip_allocations": jsontree})
    pika_channel.publish_compressed("www", "client", body)

# add all the collision domains


    raise SystemExit

    
def allocate_ips2(G_ip):
    log.info("Allocating IP addresses")
    from netaddr import IPNetwork
    address_block = IPNetwork("10.0.0.0/8")
    subnet_address_blocks = address_block.subnet(16)
#TODO: need to divide this up per AS

    G_ip.data.asn_blocks = defaultdict(list)
    #print G_ip._graph
    
    G_phy = G_ip.overlay.phy
    collision_domains = list(G_ip.nodes("collision_domain"))

    routers_by_asn = G_phy.groupby("asn", G_phy.nodes(device_type="router"))

    for collision_domain in collision_domains:
        neigh_asn = list(ank_utils.neigh_attr(G_ip, collision_domain, "asn", G_phy)) #asn of neighbors
        if len(set(neigh_asn)) == 1:
            asn = set(neigh_asn).pop() # asn of any neigh, as all same
        else:
            asn = ank_utils.most_frequent(neigh_asn) # allocate cd to asn with most neighbors in it
        collision_domain.asn = asn

    cds_by_asn = G_ip.groupby("asn", G_ip.nodes("collision_domain"))

# if node or subnet has IP already allocated, then skip from this tree

    for asn in routers_by_asn:
        log.debug("Allocating IPs for ASN %s" % asn)
# Need to iterate by asn with routers, as single router AS may not have a cd
        asn_cds = cds_by_asn.get(asn) or []
        asn_cds = sorted(asn_cds)
#tree by ASN
#TODO: Add in loopbacks as a subnet also
        asn_address_block = subnet_address_blocks.next()
        G_ip.data.asn_blocks[asn].append(asn_address_block)

        # Build list of collision domains sorted by size
        size_list = defaultdict(list)
        for cd in asn_cds:
            sn_size = subnet_size(cd.degree()) # Size of this collision domain
            size_list[sn_size].append(cd)

        loopback_size = subnet_size(len(routers_by_asn[asn])) # calculate from number of routers in asn

        ip_tree = defaultdict(list) # index by level to simplify creation of tree
        try:
            current_level = min(size_list) # start at base
        except ValueError:
            current_level = loopback_size # no cds, start at loopback
        
        asn_loopback_tree_node = None #keep track of to allocate loopbacks at end
        while True:
            cds = size_list[current_level]
            cds = sorted(cds, key = lambda x: x.node_id)
# initialse with leaves
#TODO: see if can get loopback on leftmost of tree -> then can have allocated with .1 .2 etc rather than .19 .20 etc
            ip_tree[current_level] += list(TreeNode(cd=cd) for cd in sorted(cds))
            if current_level == loopback_size:
                asn_loopback_tree_node = TreeNode(cd = "loopback")
                ip_tree[current_level].append(asn_loopback_tree_node)

            # now connect up at parent level
            tree_nodes = sorted(ip_tree[current_level]) # both leaves and parents of lower level
            pairs = list(itertools.izip(tree_nodes[::2], tree_nodes[1::2]))
            for left, right in pairs:
                ip_tree[current_level+1].append(TreeNode(left, right))
            if len(tree_nodes) % 2 == 1:
# odd number of tree nodes, add 
                final_tree_node = tree_nodes[-1]
                ip_tree[current_level+1].append(TreeNode(final_tree_node, None))

            current_level += 1
            if asn_loopback_tree_node and len(ip_tree[current_level]) < 2:
                # loopback has been allocated, and reached top of tree
                break

            #if leaf, assign back to collision domain

        # allocate to tree
        subnet_bits = 32 - max(ip_tree)
        tree_subnet = asn_address_block.subnet(subnet_bits)
        tree_root = ip_tree[max(ip_tree)].pop() # only one node at highest level (root)
        tree_root.subnet = tree_subnet.next()
        allocate_to_tree_node(tree_root)
        #walk_tree(tree_root)
        allocate_ips_to_cds(tree_root)

        my_tree = Tree(tree_root, asn)
        my_tree.save()
        tree_json = my_tree.json()
        body = json.dumps({"ip_allocations": tree_json})
        pika_channel.publish_compressed("www", "client", body)

        # Get loopback from loopback tree node
        loopback_hosts = asn_loopback_tree_node.subnet.iter_hosts()
        #router.loopback = loopback_hosts.next()
        for router in sorted(routers_by_asn[asn], key = lambda x: x.label):
            router.overlay.ip.loopback = loopback_hosts.next()

        # now allocate to the links of each cd
        for cd in asn_cds:
            hosts = cd.subnet.iter_hosts()
            for edge in sorted(cd.edges()):
                edge.ip_address = hosts.next()
