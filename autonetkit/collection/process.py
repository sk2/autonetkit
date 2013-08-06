def build_reverse_mappings_from_nidb(nidb):
    """Builds IP reverse mappings from NIDB"""
    rev_map = {
            "subnets": {},
            "loopbacks": {},
            "infra_interfaces": {},
    }

    for node in nidb:
        if node.collision_domain:
            rev_map["subnets"][str(node.ipv4_subnet)] = node
        else:
            rev_map["loopbacks"][str(node.loopback)] = node
            for interface in node.physical_interfaces:
                rev_map["infra_interfaces"][str(interface.ipv4_address)] = interface

    return rev_map

def process_traceroute(template_file, data):
    """
    TODO: make template return data other than just hops, and have reverse_map_path() handle accordingly
    """
    import textfsm
    with open(template_file, "r") as template:
        re_table = textfsm.TextFSM(template)

    routes = re_table.ParseText(data)
    header = re_table.header
    return header, routes

def extract_path_from_parsed_traceroute(header, routes, hop_id = "Hop"):
    """Returns the hop IPs from the TextFSM returned data"""
    hop_index = header.index(hop_id)
    return [item[hop_index] for item in routes]

def reverse_map_path(rev_map, path, interfaces = False):
    """Returns list of nodes in path
    interfaces selects whether to return only nodes, or interfaces
    e.g. eth0.r1 or just r1
    """

    result = []
    for hop in path:
        if hop in rev_map['infra_interfaces']:
            iface = rev_map['infra_interfaces'][hop]
            if interfaces:
                result.append(iface)
            else:
                result.append(iface.node)
        elif hop in rev_map['loopbacks']:
            node = rev_map['loopbacks'][hop]
            result.append(node)

    return result
