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

def build_reverse_mappings_from_anm_input(anm):
    """Builds reverse mappings from ANM input graph,
    assumes addresses have already been allocated onto input graph,
    either externally or by previous run"""
    g_in = anm['input']
    rev_map = {
            "loopbacks": {},
            "infra_interfaces": {},
    }

    for node in g_in:
        rev_map["loopbacks"][str(node.loopback_v4)] = node
        for interface in node.physical_interfaces:
            rev_map["infra_interfaces"][str(interface.ipv4_address)] = interface

    return rev_map


def process_textfsm(template_file, data):
    """
    TODO: make template return data other than just hops, and have reverse_map_path() handle accordingly
    """
    import textfsm
    with open(template_file, "r") as template:
        re_table = textfsm.TextFSM(template)

    data = re_table.ParseText(data)
    header = re_table.header
    return header, data

def extract_route_from_parsed_routing_table(header, routes, proto_id = "Proto",
    network_id = "Network", via_id = "Via"):
    network_index = header.index(network_id)
    proto_index = header.index(proto_id)
    via_index = header.index(via_id)
    return [(item[proto_index], item[network_index], item[via_index]) for item in routes]

def extract_path_from_parsed_traceroute(header, routes, hop_id = "Hop"):
    """Returns the hop IPs from the TextFSM returned data"""
    hop_index = header.index(hop_id)
    return [item[hop_index] for item in routes]

def reverse_map_routing(rev_map, data):
    """Returns list of nodes in path
    interfaces selects whether to return only nodes, or interfaces
    e.g. eth0.r1 or just r1
    """

    #print data

    result = []
    for protocol, network, via in data:
        print "reversing", protocol, network, via
        if network in rev_map['subnets']:
            cd = rev_map['subnets'][network]
            if via is None:
                result.append((protocol, cd, None))

            if via in rev_map['infra_interfaces']:
                iface = rev_map['infra_interfaces'][via]
                print "adding", protocol, cd, iface.node
                result.append((protocol, cd, iface.node))
    return result



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
