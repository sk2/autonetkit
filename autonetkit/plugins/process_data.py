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
    print "\t".join(re_table.header)
    for route in routes:
        print "\t".join(route)
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
            if str(interface.ip_address) == address:
                return (interface.id, node)
            
    return None 

def reverse_tap_lookup(nidb, address):
    for node in nidb.nodes("is_l3device"):
        if str(node.tap.ip) == address:
            return node
