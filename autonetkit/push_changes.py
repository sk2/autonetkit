import autonetkit.ank_messaging as ank_messaging
import autonetkit.measure as measure
import autonetkit.log as log

def apply_difference(nidb_a, nidb_diff):
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

    log.info("Differences applied")
