import autonetkit.ank_messaging as ank_messaging
import autonetkit.log as log

from autonetkit.collection.utils import get_results


def apply_difference(nidb_a, nidb_diff, emulation_server):
#TODO: batch node updates
    try:
        modified_nodes = nidb_diff['nodes']['m']
    except KeyError:
        print "no nodes modified"
        modified_nodes = {}

    ank_messaging.highlight(modified_nodes, [], [])

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

                    # TODO: use a template for this (even inline would be an improvement)
                    #TODO: can vtysh take \n delimeted data?
                    change_command = "\n".join([
                    "conf t",
                    "interface %s" % interface.id,
                    "ip ospf cost %s " % cost_2])
                    # run as vtysh -c from linux shell rather than vtysh shell
                    change_command = 'vtysh -c "%s"' % change_command

                    host = nidb_node.tap.ip
                    commands = [{"host": host, "username": "root",
                    "password": "1234","connector": "netkit",
                    "command": change_command, "vtysh": False}]
                    for response in get_results(emulation_server, commands):
                        print response["result"]

                    # and now view changed result


                    collect_command = "show ip ospf interface %s" % interface.id
                    commands = [{"host": host, "username": "root",
                    "password": "1234","connector": "netkit",
                    "command": collect_command, "vtysh": True}]
                    for response in get_results(emulation_server, commands):
                        print response["result"]

    log.info("Differences applied")
