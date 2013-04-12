import glob
import json
import time
import pprint
import autonetkit.ank_messaging as ank_messaging
import autonetkit.measure as measure

nodes = ["8"]
import autonetkit.diff

from autonetkit.nidb import NIDB

import autonetkit.verify

"""
nidb_b = NIDB()

nidb_a.restore("diff/nidb_20130411_095950.json.gz")
nidb_b.restore("diff/nidb_20130411_100005.json.gz")

import autonetkit.ank_json as ank_json

nidb_diff = autonetkit.diff.compare_nidb(nidb_a, nidb_b)
data = json.dumps(nidb_diff, cls=ank_json.AnkEncoder, indent=4)
#with open("diff.json", "w") as fh:  # TODO: make file specified in config
    #fh.write(data)
"""
#pprint.pprint(nidb_diff)

#TODO: write monitor that checks to see if latest file has changed in version directory

actions = {"_interfaces": {
    "ospf_cost": "sh ip route",
    }
    }

nidb_versions_dir = "../versions/nidb/"
nidb_a = NIDB()
#TODO: need to restore second latest, as may have changed tap ips since then
previous_timestamp = 0
while True:
    nidb_a.restore_latest(nidb_versions_dir)
    if nidb_a.timestamp == previous_timestamp:
        time.sleep(1)
    else:
        previous_timestamp = nidb_a.timestamp
        nidb_diffs = autonetkit.diff.nidb_diff(nidb_versions_dir)
        nidb_diff = nidb_diffs[0]

        print nidb_diff

        try:
            modified_nodes = nidb_diff['nodes']['m']
        except KeyError:
            print "no nodes modified"
            modified_nodes = {}
            
        ank_messaging.highlight(modified_nodes, [], [])

        highlight_nodes = [nidb_a.node(n) for n in modified_nodes]

        for node_id, node_data in modified_nodes.items():
            nidb_node = nidb_a.node(node_id)
            #print nidb_node.tap.ip
            if "_interfaces" in node_data:
                for interface_id, interface_data in node_data['_interfaces'].items():
                    interface = nidb_node.interface(interface_id)

                    if 'ospf_cost' in interface_data:
                        cost_1 = interface_data['ospf_cost'][1]
                        cost_2 = interface_data['ospf_cost'][2]

                        #print "%s (%s) ospf_cost %s -> %s" % (interface.id, interface.description,
                                #cost_1, cost_2)

                        # TODO: use a template for this
                        #TODO: can vtysh take \n delimeted data?
                        command = "\n".join([
                        "conf t",
                        "interface %s" % interface.id,
                        "ip ospf cost %s " % cost_2])

                        command = 'vtysh -c "%s"' % command
                        
                        remote_hosts = [nidb_node.tap.ip]
                        measure.send(nidb_a, command, remote_hosts)
                        command = "show ip ospf interface %s" % interface.id
                        command = 'vtysh -c "%s"' % command
                        measure.send(nidb_a, command, remote_hosts)
