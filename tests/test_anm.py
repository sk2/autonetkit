import autonetkit
import autonetkit.log as log

log.info("Testing ANM")

anm = autonetkit.anm.NetworkModel()

g_in = anm.add_overlay("input")

router_ids = ["r1", "r2", "r3", "r4", "r5"]
g_in.add_nodes_from(router_ids)

g_in.update(device_type = "router")
g_in.update(asn = 1)

positions = {'r3': (107, 250), 'r5': (380, 290), 'r1': (22, 50), 'r2': (377, 9), 'r4': (571, 229)}
for node in g_in:
    node.x = positions[node][0]
    node.y = positions[node][1]
    eth0 = node.add_interface("eth0")
    eth0.speed = 100

# node->node edges
input_edges = [("r1", "r2"), ("r2", "r4"), ("r3", "r4"), ("r3", "r5"), ("r1", "r3")]
input_interface_edges = [(g_in.node(src).interface(1), g_in.node(dst).interface(1)) for src, dst in input_edges]
g_in.add_edges_from(input_interface_edges)

g_phy = anm['phy']
g_phy.add_nodes_from(g_in, retain=["device_type", "x", "y", "asn"])
g_phy.add_edges_from(g_in.edges())

g_test = anm.add_overlay("test")
g_test.add_node("test_node")

# test interfaces
for node in g_phy:
    pass

test_node = g_phy.node("r1")

#TODO: assert here
node_interfaces = list(test_node.interfaces())
# test equality
#TODO: check why == uses eq() but != doesn't...
assert(not node_interfaces[0] == node_interfaces[1])

print list(test_node.interfaces())
for i in test_node.interfaces():
    print i, i.dump()

print [i.description for i in sorted(node_interfaces)]

assert ([i.description for i in sorted(node_interfaces)] == ['loopback', 'eth0'])


for interface in test_node:
    # test exists
    assert(interface is not None)
    # test __nonzero__
    assert(interface)
    set_value = 123
    interface.test = set_value
    get_value = interface.test
    assert(set_value == get_value) # TODO: could check is indeed same object reference


loopback0 = test_node.interface(0)
assert(not loopback0.is_bound)
assert(loopback0.is_loopback)
assert(not loopback0.is_physical)
assert(loopback0.is_loopback_zero)

#TODO: need to add more loopbacks to test
assert(str(loopback0) == "loopback.r1")

eth0 = test_node.interface(1)
assert(eth0.is_bound)
assert(not eth0.is_loopback)
assert(not eth0.is_loopback_zero)
assert(eth0.is_physical)

assert(eth0.phy == eth0) # should be itself as phy overlay

#print eth0.dump()

#Cross-layer access
assert(eth0['input'] is not None)

assert(eth0.neighbors() == [g_phy.node("r2").interface(1), g_phy.node("r3").interface(1)])

# access non existent overlay
#TODO: decide if worth trying to assert the logged item
eth0["non_existent_overlay"]
# Need to test cross-layer interface access to phy

#test accessing overlay for node that doesnt exist in that overlay
test_overlay_node = g_test.node("test_node")
test_overlay_interface = test_overlay_node.add_interface()
test_overlay_interface['phy']

#Want to assertRaises


# Test edges
autonetkit.update_http(anm)
test_edge = g_in.edge("r1", "r2")
assert(test_edge is not None)

# test overlays

# test ANM
test_node = g_phy.node("r1")
assert(test_node.asn == 1)
assert(test_node.device_type == "router")
#TODO: also need to test for servers
assert(test_node.is_l3device())
assert(test_node.is_router())
assert(not test_node.is_switch())
assert(not test_node.is_server())
assert(str(list(test_node.neighbors())) == "[r2, r3]")
assert(str(list(test_node.neighbor_interfaces())) == "[eth0.r2, eth0.r3]")
# Test getting from another overlay
assert(test_node['input'].asn == 1)

assert(str(sorted(g_phy.nodes())) == "[r1, r2, r3, r4, r5]")

assert(test_node.label == "r1")


"""
g_in.update("r4", asn = 2)
g_in.update(["r1", "r2", "r3"], asn = 1)

test = g_in.node("r5")

"""
# More graph level tests
#TODO: need to allow searching for interface by .interface("eth1", "r1")

#TODO: need to provide remove_nodes_from

test_node = g_phy.node("r1")
search_int = list(test_node.interfaces())[0]
result_int = g_phy.interface(search_int)
assert(search_int == result_int)

search_int = list(test_node.interfaces())[1]
result_int = g_phy.interface(search_int)
assert(search_int == result_int)

assert(g_phy.node("r1").degree() == 2)
assert(g_phy.node("r3").degree() == 3)

g_phy.add_edge("r1", "r4")
assert(g_phy.edge("r1", "r4") is not None)

edges_to_remove = g_phy.edge("r1", "r4")
#TODO: remove_edges_from needs to support single/list
g_phy.remove_edges_from([edges_to_remove])
assert(g_phy.edge("r1", "r4") is None)

src_int =  g_phy.node("r1").add_interface("eth1")
dst_int =  g_phy.node("r5").add_interface("eth1")
g_phy.add_edges_from([(src_int, dst_int)])
edge = g_phy.edge("r1", "r5")
assert((edge.src_int, edge.dst_int) == (src_int, dst_int))


edge_a1 = g_phy.edge("r1", "r2")
edge_a2 = g_phy.edge("r1", "r2")
assert(edge_a1 == edge_a2)
edge_b = g_phy.edge("r1", "r2")
assert(edge_a1 != edge_b)

# compare to string
assert(edge_a1 == ("r1", "r2"))
assert(edge_a1 != ("r1", "r3"))

assert(bool(edge_a1) is True) #exists
edge_non_existent = g_phy.edge("r1", "r8")
#TODO: need to document API to check exists/doesn't exist for nodes, edges, interfaces, graphs,....
assert(bool(edge_non_existent) is False) #doesn't exist

# add node
#TODO: better handling of nodes with no x,y, asn, etc in jsonify
r6 = g_phy.add_node("r6")
assert(r6 in g_phy)
del g_phy[r6]
assert(r6 not in g_phy)


# graph data
g_phy.data.test = 123
assert(g_phy.data.test == 123)
assert(g_phy.data['test'] == 123)

# test adding a node with not attributes for jsonify

#TODO: test for directed graph

autonetkit.update_http(anm)