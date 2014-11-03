import autonetkit.ank as ank_utils
import autonetkit.log as log

"""TODO: map the log info/warning/debug to functions here
# which then map to the appropriate log function, so that can handle either be verbose or not verbose to console with test information.
"""


def validate(anm):
    log.debug("Validating overlay topologies")
    tests_passed = True
    tests_passed = validate_ipv4(anm) and tests_passed

    try:
        from autonetkit_cisco import ank_validate as cisco_validate
    except ImportError, e:
        log.debug("Unable to load autonetkit_cisco %s" % e)
    else:
        cisco_validate.validate(anm)

    validate_ibgp(anm)
    validate_igp(anm)
    check_for_selfloops(anm)
    all_nodes_have_asn(anm)

    if tests_passed:
        log.debug("All validation tests passed.")
    else:
        log.warning("Some validation tests failed.")


def check_for_selfloops(anm):
    # checks each overlay for selfloops
    for overlay in anm:
        selfloop_count = overlay._graph.number_of_selfloops()
        if selfloop_count > 0:
            log.warning("%s has %s self-loops" % (overlay, selfloop_count))


def all_nodes_have_asn(anm):
    g_phy = anm['phy']
    for node in g_phy.l3devices():
        if node.asn is None:
            log.warning("No ASN set for physical device %s" % node)


def validate_ibgp(anm):
    import networkx as nx
    # TODO: repeat for ibgp v6
    # TODO: test if overlay is present, if not then warn
    if not anm.has_overlay("ibgp_v4"):
        return  # no ibgp v4  - eg if ip addressing disabled

    g_ibgp_v4 = anm['ibgp_v4']

    for asn, devices in ank_utils.groupby("asn", g_ibgp_v4):
        asn_subgraph = g_ibgp_v4.subgraph(devices)
        graph = asn_subgraph._graph
        # get subgraph
        if not nx.is_strongly_connected(graph):
            g_ibgp_v4.log.warning(
                "iBGP v4 topology for ASN%s is disconnected" % asn)
            # TODO: list connected components - but not the primary?
        else:
            g_ibgp_v4.log.debug(
                "iBGP v4 topology for ASN%s is connected" % asn)


def validate_igp(anm):
    import networkx as nx
    # TODO: test if overlay is present, if not then warn
    if not anm.has_overlay("igp"):
        return  # no ibgp v4  - eg if ip addressing disabled

    g_igp = anm['igp']

    for asn, devices in ank_utils.groupby("asn", g_igp):
        if asn is None:
            continue
        asn_subgraph = g_igp.subgraph(devices)
        graph = asn_subgraph._graph
        # get subgraph
        if not nx.is_connected(graph):
            g_igp.log.warning("IGP topology for ASN%s is disconnected" % asn)
            # TODO: list connected components - but not the primary?
        else:
            g_igp.log.debug("IGP topology for ASN%s is connected" % asn)


def all_same(items):
    # based on http://stackoverflow.com/q/3787908
    # use all with generator as shortcuts to false as soon as one invalid
    # TODO: place this into generic ANK functions, use similar shortcut for
    # speed elsewhere, in other utility functions
    return all(x == items[0] for x in items)


def all_unique(items):
    # based on http://stackoverflow.com/q/3787908
    # shortcuts for efficiency
    seen = set()
    return not any(i in seen or seen.add(i) for i in items)


def duplicate_items(items):
    unique = set(items)
    counts = {i: items.count(i) for i in unique}
    return [i for i in counts if counts[i] > 1]

# TODO: add high-level symmetry, anti-summetry, uniqueness, etc functions
# as per NCGuard

# TODO: make generic interface equal or unique function that takes attr


def validate_ipv4(anm):
    # TODO: make this generic to also handle IPv6
    if not anm.has_overlay("ipv4"):
        log.debug("No IPv4 overlay created, skipping ipv4 validation")
        return
    g_ipv4 = anm['ipv4']
    # interface IP uniqueness
    tests_passed = True

    # TODO: only include bound interfaces

    # check globally unique ip addresses
    all_ints = [i for n in g_ipv4.l3devices()
                for i in n.physical_interfaces()
                if i.is_bound]  # don't include unbound interfaces
    all_int_ips = [i.ip_address for i in all_ints if i.ip_address]

    if all_unique(all_int_ips):
        g_ipv4.log.debug("All interface IPs globally unique")
    else:
        tests_passed = False
        duplicates = duplicate_items(all_int_ips)
        duplicate_ips = set(duplicate_items(all_int_ips))
        duplicate_ints = [n for n in all_ints
                          if n.ip_address in duplicate_ips]
        duplicates = ", ".join("%s: %s" % (i.node, i.ip_address)
                               for i in duplicate_ints)
        g_ipv4.log.warning("Global duplicate IP addresses %s" % duplicates)

    for bc in g_ipv4.nodes("broadcast_domain"):
        bc.log.debug("Verifying subnet and interface IPs")
        if not bc.allocate:
            log.debug("Skipping validation of manually allocated broadcast "
                "domain %s" % bc)
            continue

        neigh_ints = list(bc.neighbor_interfaces())
        neigh_ints = [i for i in neigh_ints if i.node.is_l3device()]
        neigh_int_subnets = [i.subnet for i in neigh_ints]
        if all_same(neigh_int_subnets):
            # log ok
            pass
        else:
            subnets = ", ".join("%s: %s" % (i.node, i.subnets)
                                for i in neigh_int_subnets)
            tests_passed = False
            log.warning("Different subnets on %s. %s" %
                        (bc, subnets))
            # log warning

        ip_subnet_mismatches = [i for i in neigh_ints
                                if i.ip_address not in i.subnet]
        if len(ip_subnet_mismatches):
            tests_passed = False
            mismatches = ", ".join("%s not in %s on %s" %
                                   (i.ip_address, i.subnet, i.node)
                                   for i in ip_subnet_mismatches)
            bc.log.warning("Mismatched IP subnets: %s" %
                           mismatches)
        else:
            bc.log.debug("All subnets match")

        neigh_int_ips = [i.ip_address for i in neigh_ints]
        if all_unique(neigh_int_ips):
            bc.log.debug("All interface IP addresses are unique")
            duplicates = duplicate_items(neigh_int_ips)
        else:
            tests_passed = False
            duplicate_ips = set(duplicate_items(neigh_int_ips))
            duplicate_ints = [n for n in neigh_ints
                              if n.ip_address in duplicate_ips]
            duplicates = ", ".join("%s: %s" % (i.node, i.ip_address)
                                   for i in duplicate_ints)
            bc.log.warning("Duplicate IP addresses: %s" % duplicates)

    if tests_passed:
        g_ipv4.log.debug("All IP tests passed.")
    else:
        g_ipv4.log.warning("Some IP tests failed.")

    return tests_passed
