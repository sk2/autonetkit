import autonetkit.log as log
import pkg_resources
try:
    import textfsm
except ImportError:
    log.info("Unable to import TextFSM")

def sh_ip_route(nidb, data):
    template_file = pkg_resources.resource_filename(__name__, "../textfsm/quagga/sh_ip_route")
    template = open(template_file)
    re_table = textfsm.TextFSM(template)
    routes = re_table.ParseText(data)
    print "\t".join(routes)
    return

def traceroute(nidb, data):
    template_file = pkg_resources.resource_filename(__name__, "../textfsm/linux/traceroute")
    template = open(template_file)
    re_table = textfsm.TextFSM(template)
    routes = re_table.ParseText(data)
    #print "\t".join(re_table.header)
    for route in routes:
        #print "\t".join(route)
        route = route[0] # first element of table: todo make this programatic from table.header
        #print reverse_lookup(nidb, route)

    try:
        return [reverse_lookup(nidb, route[0])[1] for route in routes]
    except TypeError:
        log.info("Unable to parse %s" % routes)
        return []


def reverse_lookup(nidb, address):
    for node in nidb.nodes("is_l3device"):
        if str(node.loopback) == address:
            return ("loopback", node)

        for interface in node.interfaces:
            if str(interface.ipv4_address) == address:
                return (interface.id, node)
            
    return None 

def reverse_tap_lookup(nidb, address):
    for node in nidb.nodes("is_l3device"):
        if str(node.tap.ip) == address:
            return node


def parse_sh_ip_route(anm, nidb, data):
    #TODO: Split this from being seperate module to being a workable function
    #TODO: need to copy across subnet to collision domain in nidb

    import pprint

    with open("test.txt", "r") as fh:
        data = fh.read()

    template_file = pkg_resources.resource_filename(__name__, "textfsm/quagga/sh_ip_route")
    template = open(template_file)
    re_table = textfsm.TextFSM(template)
    routes = re_table.ParseText(data)


    pprint.pprint(routes)

    with open("test_out.txt", "w") as fh:
        fh.write(pprint.pformat(routes, width=200))

    from autonetkit.nidb import NIDB
    nidb = NIDB()
    nidb.restore_latest()

    subnets = {}
    loopbacks = {}
    infra_interfaces = {}

    from autonetkit.anm import AbstractNetworkModel
    anm = AbstractNetworkModel()
    anm.restore_latest()
    for node in anm['ipv4']:
        if node.collision_domain:
            subnets[str(node.subnet)] = node
        else:
            loopbacks[str(node.loopback)] = node
            for interface in node:
                # find interface in nidb
                #nidb_interface = nidb.interface(interface)
                infra_interfaces[str(interface.ip_address)] = interface

    pprint.pprint(subnets)

    pprint.pprint(["%s: %s.%s" % (subnet, nidb.interface(i).id, i.node)
            for (subnet, i) in infra_interfaces.items()])

    mapped_routes = []
    for route_entry in routes:
        pass
        try:
            route_entry[3] = subnets[route_entry[3]]
        except KeyError:
            continue

        try:
            route_entry[4] = infra_interfaces[route_entry[4]]
        except KeyError:
            continue

        mapped_routes.append((route_entry[3], route_entry[4]))


    start_node = anm['ipv4'].node("8")

    nodes = [r[0] for r in mapped_routes]
    nodes = []
    edges = []
    paths = [[start_node, r[1].node, r[0]] for r in mapped_routes]
    pprint.pprint(paths)

    import autonetkit.ank_messaging as ank_messaging
    ank_messaging.highlight(nodes, edges, paths)
            
