import json
import sys
import autonetkit.log as log
from autonetkit.collection.utils import get_results
import pkg_resources
import autonetkit.collection.process as ank_process
import autonetkit.ank_messaging as ank_messaging
import autonetkit

import pkg_resources
parse_template = pkg_resources.resource_filename("autonetkit", "textfsm/linux/traceroute")

anm = autonetkit.ANM()
anm.restore_latest()

nidb = autonetkit.NIDB()
nidb.restore_latest()
print list(nidb.nodes())

autonetkit.update_http(anm, nidb)

emulation_server = "115.146.93.18"
command_list = []

import autonetkit.collection.process as ank_process
reverse_mappings = ank_process.build_reverse_mappings_from_nidb(nidb)





import random
dest_node = random.choice(list(nidb.routers()))
#dest_node = nidb.node("as1r1")
#dest_node = nidb.node("as40r1")
#dest_label = random.choice(["as1r1", "as30r1", "as20r3"])
#dest_node = nidb.node(dest_label)
dest_ip = dest_node.interfaces[1].ipv4_address
command = "traceroute -n -a -U -w 0.5 %s" % dest_ip

import networkx as nx
g_ospf = anm['ospf']
graph_ospf = g_ospf._graph
spf = nx.all_pairs_dijkstra_path(graph_ospf, weight="cost")
print "SPF"
print spf

for node in nidb.routers():
    host = node.tap.ip
    cmd = {"host": host, "username": "root",
    "password": "1234","connector": "netkit",
    "original_node": str(node),
    "command": command}
    command_list.append(cmd)

for response in get_results(emulation_server, command_list):
        data = response["result"]
        #print "response is", response
        header, parsed_data = ank_process.process_textfsm(parse_template, data)
        path = ank_process.extract_path_from_parsed_traceroute(header, parsed_data)
        #print "path", path
        mapped = ank_process.reverse_map_path(reverse_mappings, path)
        if len(mapped):
            print mapped
            original_command = json.loads(response["command"])
            original_node = original_command["original_node"]
            mapped.insert(0, original_node) # prepend first hop
            destination = mapped[-1]
            #print "expected", original_node, "to", destination
            #print "spf is", spf[original_node][destination]
            #print "got", mapped
            ank_messaging.highlight(path = mapped )
