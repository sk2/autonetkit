import autonetkit
import autonetkit.log as log


anm = autonetkit.anm.NetworkModel()
g_phy = anm.add_overlay("phy")
for index in range(5):
    node_id = "r_%s" % index
    g_phy.add_node(node_id)

print g_phy.nodes()
for node in g_phy:
    print node
    print node._ports
    for interface in range(3):
        node.add_interface()

sw = g_phy.add_node("sw1")
sw.device_type = "switch"

for node in g_phy:
    for iface in node:
        g_phy.add_edge(sw, iface)
        print sw.edges()


for edge in g_phy.edges():
    print edge._ports
