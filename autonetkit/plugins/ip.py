import time
from collections import defaultdict
import json
import itertools
import os
import autonetkit.ank as ank_utils
import autonetkit.log as log

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
#TODO: try cPickle
        pickle_dir = os.path.join("versions", "ip")
        if not os.path.isdir(pickle_dir):
            os.makedirs(pickle_dir)

        pickle_file = "ip_as%s_%s.pickle.tar.gz" % (self.asn, self.timestamp)
        pickle_path = os.path.join(pickle_dir, pickle_file)
        with open(pickle_path, "wb") as pickle_fh:
            pickle.dump(self, pickle_fh, -1)

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
                    "name": str(node),
                    "children": nodes,
                }

        return {"name": str(node)}


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

    
def allocate_ips(G_ip):
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
        log.info("Allocating IPs for ASN %s" % asn)
# Need to iterate by asn with routers, as single router AS may not have a cd
        asn_cds = cds_by_asn.get(asn) or []
        asn_cds = sorted(asn_cds)
#tree by ASN
#TODO: Add in loopbacks as a subnet also
        asn_address_block = subnet_address_blocks.next()
        #print "ips for asn", asn
        G_ip.data.asn_blocks[asn].append(asn_address_block)
#TODO: record this in G_ip graph data not node/edge data

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

        #TODO: Also want to store this ordering of what is assigned to which node, not just the tree...

        # traverse tree, allocate back to loopbacks, and to nodes
        # TODO: should loopbacks be a sentinel type node for faster traversal rather than checking each time?

