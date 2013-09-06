import autonetkit.log as log

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

    from collections import defaultdict
    import netaddr

    g_in = anm['input']
    rev_map = {
            "loopbacks": {},
            "infra_interfaces": {},
            "subnets": {},
    }

    subnets = defaultdict(list)

    for node in g_in:
        rev_map["loopbacks"][str(node.loopback_v4)] = node
        for interface in node.physical_interfaces:
            rev_map["infra_interfaces"][str(interface.ipv4_address)] = interface

            prefixlen = interface.ipv4_prefixlen
            cidr_string = "%s/%s" % (interface.ipv4_address, prefixlen)
            intermediate_subnet = netaddr.IPNetwork(cidr_string)
            subnet_cidr_string = "%s/%s" % (intermediate_subnet.network, prefixlen)
            subnet = netaddr.IPNetwork(subnet_cidr_string)
            subnets[subnet].append(interface)

    for subnet, interfaces in subnets.items():
        subnet_str = str(subnet)
        rev_map['subnets'][subnet_str] = "_".join(str(i.node) for i in interfaces)

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


def reverse_map_address(rev_map, address, interfaces = False):
    if address in rev_map['infra_interfaces']:
        iface = rev_map['infra_interfaces'][address]
        if interfaces:
            return iface
        else:
            return iface.node
    elif address in rev_map['loopbacks']:
        node = rev_map['loopbacks'][address]
        return node


def extract_node_path_info(header, parsed_data, mapped_data, exclude_keys = None):
    if len(parsed_data) != len(mapped_data):
        log.warning("Parsed data different length to mapped data, not extracting node data")

    if exclude_keys:
        exclude_keys = set(exclude_keys)
    else:
        exclude_keys = set() # empty set for simpler test logic

    retval = []
    for index, hop in enumerate(mapped_data):
        node_vals = parsed_data[index] # TextFSM output for this hop
        node_data = dict(zip(header, node_vals))

        filtered_data = {k: v for k, v in node_data.items()
        if len(v) and k not in exclude_keys}
        filtered_data['host'] = str(hop.id)
        retval.append(filtered_data)

    return retval

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

def substitute_ips(data, rev_map, interfaces = False):
    import re
    re_ip_address = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    re_ip_loopback= r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/32"
    re_ip_subnet = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}"
    if not len(data):
        log.info("No data provided to IP substitution, returning")
        return data

    def replace_ip(match):
      match = match.group()
      if match in rev_map['infra_interfaces']:
        iface = rev_map['infra_interfaces'][match]
        if interfaces:
            named = "%s.%s" %(iface.id, iface.node)
            return named
        else:
            return str(iface.node)
      return match # no match, return the raw IP

    def replace_loopbacks(match):
      match = match.group()
      # strip off the /32
      loopback_ip = match[:-3]
      if loopback_ip in rev_map['loopbacks']:
        node = rev_map['loopbacks'][loopback_ip]
        return str(node)
      return match # no match, return the raw IP

    def replace_loopbacks_no_mask(match):
      #TODO: refactor
      match = match.group()
      # strip off the /32
      loopback_ip = match
      if loopback_ip in rev_map['loopbacks']:
        node = rev_map['loopbacks'][loopback_ip]
        return str(node)
      return match # no match, return the raw IP

    def replace_subnet(match):
      match = match.group()

      if match in rev_map['subnets']:
        subnet = rev_map['subnets'][match]
        return str(subnet)
      return match # no match, return the raw IP

    # do loopbacks first
    data = re.sub(re_ip_loopback, replace_loopbacks, data)
    data = re.sub(re_ip_address, replace_ip, data)
    # try for ip addresses in loopback
    data = re.sub(re_ip_address, replace_loopbacks_no_mask, data)
    # and for subnets ie ip/netmask
    return re.sub(re_ip_subnet, replace_subnet, data)
