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

#TODO: Should have two nodes: SubnetNode and a HostNode

class TreeNode(object):
    def __init__(self, prefixlen, host = None):
        self.subnet = None
        self.address = None
        self.prefixlen = prefixlen
        self.host = host
        self.group_attr = None

    def __repr__(self):
        if self.subnet and self.host:
            return "%s, %s" % (self.host, self.formatted_subnet)
        if self.subnet and self.group_attr:
            return "%s, %s" % (self.formatted_subnet, self.group_attr)
        if self.host:
            return "%s" % (self.host)
        if self.subnet:
            return "%s" % self.formatted_subnet
        return "/%s" % self.prefixlen

    @property
    def formatted_subnet(self):
        return self.subnet
        try:
            prefixlen = self.subnet.prefixlen
        except AttributeError:
            return self.subnet
        octets = str(self.subnet.network).split(".")
        if prefixlen > 24:
            return ".".join([octets[3]])
        elif prefixlen > 16:
            return ".".join([octets[2], octets[3]])
        elif prefixlen > 8:
            return ".".join([octets[1], octets[2], octets[3]])

    def is_subnet(self):
        return not (self.host or self.group_attr) # if no host node, then is a subnet

    def is_host(self):
        return self.host

    def is_collision_domain(self):
        return self.is_host() and self.host.collision_domain

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
        subgraphs = []

        unallocated_nodes = self.unallocated_nodes
        unallocated_nodes = sorted(unallocated_nodes, key = lambda x: x.get(group_attr))
        for attr_value, items in itertools.groupby(unallocated_nodes, key = lambda x: x.get(group_attr)):
# make subtree for each attr
            items = list(items)
            subgraph = nx.DiGraph()
            for item in items:
                if item.collision_domain:
                    cd_node = TreeNode(prefixlen = 32 - subnet_size(item.degree()), host = item) 
                    subgraph.add_node(cd_node)
                if item.is_l3device:
                    subgraph.add_node(TreeNode(prefixlen = 32, host = item))

            # now group by levels
            level_counts = defaultdict(int)

            nodes_by_level = defaultdict(list)
            for node in subgraph.nodes():
                nodes_by_level[node.prefixlen].append(node)

            for level, nodes in nodes_by_level.items():
                level_counts[level] = len(nodes)

            add_parent_nodes(subgraph, level_counts)

            # rebuild with parent nodes
            nodes_by_level = defaultdict(list)
            for node in subgraph.nodes():
                nodes_by_level[node.prefixlen].append(node)

            root_node = build_tree(subgraph, level_counts, nodes_by_level)
            subgraphs.append(subgraph)

            subgraph.graph['root'] = root_node
            root_node.group_attr = attr_value

        global_graph = nx.DiGraph()
        subgraphs = sorted(subgraphs, key = lambda x: subgraph.graph['root'].group_attr)
        subgraphs = [subgraphs[0]]
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
        nodes_by_level = defaultdict(list)
        for node in global_graph:
            nodes_by_level[node.prefixlen].append(node)

        global_root = build_tree(global_graph, level_counts, nodes_by_level)

        for subgraph in subgraphs:
            print "sn nodes", subgraph.nodes()
            global_graph = nx.compose(global_graph, subgraph)

        # now allocate the IPs
        global_ip_block = netaddr.IPNetwork("192.168.0.0/%s" %global_root.prefixlen)

        def allocate(graph, node):
            children = graph.successors(node)
            prefixlen = node.prefixlen
            subnet = node.subnet.subnet(prefixlen+1)
            for child in children:
                if child.is_collision_domain():
                    child.subnet = subnet.next()
                    iterhosts = child.subnet.iter_hosts()
                    sub_children = graph.successors(child)
                    for sub_child in sub_children:
                        sub_child.subnet = iterhosts.next()
                        #print "alloc sub_child to", sub_child, iterhosts.next()
                     
                elif not child.is_host():
                    child.subnet = subnet.next()
                    #TODO: tidy up this logic with node types
                    allocate(graph, child)
                else:
                    #print "dont allocate to child", child
                    #print "child isnt host"
                    #child.subnet = subnet.next()
                    child.subnet = subnet.next()
                    pass

        global_root.subnet = global_ip_block
        allocate(global_graph, global_root)

        self.graph = global_graph
        self.root_node = global_root

        group_allocations = {}
        for node in global_graph:
            if node.group_attr:
                group_allocations[node.group_attr] = node.subnet
        #print group_allocations
#TODO: Store these back into G_ip

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
            successors = self.graph.successors(node)
            if successors:
                children = [list_successors(n) for n in successors]
                return {"name": node,
                        "subnet": node.subnet,
                        "children": children}
            return {"name": node, "subnet": node.subnet}

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
    
    body = json.dumps({"ip_allocations": jsontree})
    pika_channel.publish_compressed("www", "client", body)
    for node in ip_tree.graph:
        if node.host:
            host = node.host
            if host.collision_domain:
                #print "host is CD", host
                for child in ip_tree.graph.successors(node):
                    child_host = child.host
                    edge = G_ip.edge(host, child_host)
                    #print "child has subnet", child.subnet
            else:
                #print "host"
                pass

    raise SystemExit

# add all the collision domains
    for node in G_ip.nodes("collision_domain"):
        print "coll dom", node, node.subnet
        
    for node in G_ip.nodes("is_l3device"):
        print "lo", node.loopback
        for edge in node.edges():
            print "link", edge.ip_address

    raise SystemExit
