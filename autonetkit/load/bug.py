try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import networkx as nx
import re
import pprint
import sys

NS_virl = 'http://cide.cisco.com/VIRL/beta'

ET.register_namespace('virl', 'http://cide.cisco.com/VIRL/beta')
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
ET.register_namespace('xs', 'http://www.w3.org/2001/XMLSchema')

try:
    filename = sys.argv[1]
except IndexError:
    filename = "2.virl"
tree = ET.parse(filename)
root = tree.getroot()

#TODO: is node name guaranteed to be unique?
print "nodes"
G = nx.DiGraph()
#node_list = []
for node in root.findall("{%s}node" % NS_virl):
    #print node, node.tag, node.attrib
    #print node.get("name"), node.get("type"), node.get("location")
    #node_list.append(node.get("name"))
    label = node.get("name")
    x, y = node.get("location").split(",")
    node_type = node.get("type") or "router"
    device_subtype = ""
    if node_type == "NETMAP_CONNECTOR":
        node_type = "switch" # for AutoNetkit
        device_subtype = "bus"
    else:
        node_type = node_type.lower() # listed in CAPS in VM-Maestro

    data = {
            'label': label,
            'device_type': node_type,
            'device_subtype': device_subtype,
            'x': float(x)/2,
            'y': float(y)/2,
            }
    G.add_node(label, data)
    for interface in node.findall("{%s}interface" % NS_virl):
        #print interface.get("name")
        pass

for connection in root.findall("{%s}connection" % NS_virl):
    #print node, node.tag, node.attrib
    #print connection.get("src"), connection.get("dst"), connection.get("style")
    src = connection.get("src")

# Xquery approach
# append NS
    src = connection.get("src")
    src_split = src.split("/")
    node_query = src_split[2]
    interface_query = None
    if len(src_split) == 4:
        interface_query = src_split[3] #optional

    node_query = "{%s}%s" % (NS_virl, node_query)
    src_node = root.find(node_query)
    if interface_query:
        interface_query = "{%s}%s" % (NS_virl, interface_query)
        src_int = src_node.find(interface_query)
        print "src: ", src_node.get("name"), src_int.get("name")
    else:
        print "src: ", src_node.get("name")

#TODO: if we use node index, then don't need to get the node name using xquery - can use just regex

    dst = connection.get("dst")
    dst_split = dst.split("/")
    node_query = dst_split[2]
    interface_query = None
    if len(dst_split) == 4:
        interface_query = dst_split[3] #optional

    node_query = "{%s}%s" % (NS_virl, node_query)
    dst_node = root.find(node_query)
    if interface_query:
        interface_query = "{%s}%s" % (NS_virl, interface_query)
        dst_int = dst_node.find(interface_query)
        print "dst: ", dst_node.get("name"), dst_int.get("name")
    else:
        print "dst: ", dst_node.get("name")

    #TODO: store src and dst interfaces on the edge data
    data = {
            'style': connection.get("style"),
            }

    G.add_edge(src_node.get("name"), dst_node.get("name"), data)

pprint.pprint(G.nodes(data=True))
pprint.pprint(G.edges(data=True))
nx.write_graphml(G, "test.graphml")

#TODO: if there are nested attributes when we may need to use json... or just pass the graph directly

# regex approach
"""
    m  = re.match("/topology/node\[(\d+)\](?:/interface\[(\d+)\])*", src)
    if m:
        src_node_index = int(m.group(1)) + 1

    dst = connection.get("dst")

    m  = re.match("/topology/node\[(\d+)\](?:/interface\[(\d+)\])*", dst)
    if m:
        dst_node_index = int(m.group(1)) + 1
        if m.group(2):
            print "dst int", m.group(2)

    print src_node_index, dst_node_index
    print "link from", node_list[src_node_index], "to", node_list[dst_node_index]
for elem in root.getiterator():
    print "elem of root", elem.tag, elem.attrib
    pass


print "searching for", "{%s}:topology" % NS_virl


for node in root.find("{%s}:node" % NS_virl):
    print node
"""
