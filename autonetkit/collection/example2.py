import autonetkit.log as log
from autonetkit.collection.utils import get_results
import pkg_resources
import autonetkit.collection.process as ank_process
import autonetkit.ank_messaging as ank_messaging
import autonetkit
import json
import random

import pkg_resources
parse_template = pkg_resources.resource_filename("autonetkit", "textfsm/quagga/sh_ip_route")

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

print reverse_mappings

command = "show ip route"

node = nidb.node("5")
#node = random.choice(list(nidb.routers()))
while True:
#for node in nidb.routers():
    host = node.tap.ip
    cmd = {"host": host, "username": "root",
    "password": "1234","connector": "netkit",
    "vtysh": True,
    "original_node": str(node),
    "command": command}
    command_list.append(cmd)
    #break

    for response in get_results(emulation_server, command_list):
            data = response["result"]
            print "response is", response
            if not response['success']:
                print "Skipping response"
                continue
            header, parsed_data = ank_process.process_textfsm(parse_template, data)
            print header, parsed_data
            extracted = ank_process.extract_route_from_parsed_routing_table(header, parsed_data)
            mapped = ank_process.reverse_map_routing(reverse_mappings, extracted)
            print "mapped", mapped
            for entry in mapped:
                print response["command"]
                original_command = json.loads(response["command"])
                original_node = original_command["original_node"]
                protocol, cd, node = entry
                if node is None:
                    #vis = [original_node, cd] # direct connection?
                    continue
                else:
                    vis = [original_node, node, cd]
                    #TODO: netx compare
                print "vis", vis
                ank_messaging.highlight(path = vis )

    import time
    time.sleep(5)
