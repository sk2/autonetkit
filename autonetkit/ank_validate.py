import autonetkit.log as log

"""TODO: map the log info/warning/debug to functions here
# which then map to the appropriate log function, so that can handle either be verbose or not verbose to console with test information.
"""

def validate(anm):
    tests_passed = True
    tests_passed = validate_ipv4(anm) and tests_passed

    if tests_passed:
        log.info("All validation tests passed.")
    else:
        log.warning("Some validation tests failed.")

def all_same(items):
    # based on http://stackoverflow.com/q/3787908
    # use all with generator as shortcuts to false as soon as one invalid
    #TODO: place this into generic ANK functions, use similar shortcut for speed elsewhere, in other utility functions
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

#TODO: add high-level symmetry, anti-summetry, uniqueness, etc functions as per NCGuard

#TODO: make generic interface equal or unique function that takes attr

def validate_ipv4(anm):
    #TODO: make this generic to also handle IPv6
    if not anm.has_overlay("ipv4"):
        log.debug("No IPv4 overlay created, skipping ipv4 validation")
        return
    g_ipv4 = anm['ipv4']
    # interface IP uniqueness
    tests_passed = True

    #TODO: only include bound interfaces

    # check globally unique ip addresses
    all_ints = [i for n in g_ipv4.nodes("is_l3device")
            for i in n.physical_interfaces
            if i.is_bound] # don't include unbound interfaces
    all_int_ips = [i.ip_address for i in all_ints]

    if all_unique(all_int_ips):
        log.debug("All interface IPs globally unique")
    else:
        tests_passed = False
        duplicates = duplicate_items(all_int_ips)
        duplicate_ips = set(duplicate_items(all_int_ips))
        duplicate_ints = [n for n in all_ints
                if n.ip_address in duplicate_ips]
        duplicates = ", ".join("%s: %s" % (i.node, i.ip_address)
            for i in duplicate_ints)
        log.warning("Global duplicate IP addresses %s" % duplicates)

    for cd in g_ipv4.nodes("collision_domain"):
        log.debug("Verifying subnet and interface IPs for %s" % cd)
        neigh_ints = list(cd.neighbor_interfaces())
        neigh_int_subnets = [i.subnet for i in neigh_ints]
        if all_same(neigh_int_subnets):
            # log ok
            pass
        else:
            subnets = ", ".join("%s: %s" % (i.node, i.subnets)
                    for i in neigh_int_subnets)
            tests_passed = False
            log.warning("Different subnets on %s. %s" %
                    (cd, subnets))
            # log warning

        ip_subnet_mismatches = [i for i in neigh_ints
                    if i.ip_address not in i.subnet]
        if len(ip_subnet_mismatches):
            tests_passed = False
            mismatches = ", ".join("%s not in %s on %s" %
                    (i.ip_address, i.subnet, i.node)
                    for i in ip_subnet_mismatches)
            log.warning("Mismatched IP subnets for %s: %s" %
                    (cd, mismatches))
        else:
            log.debug("All subnets match for %s" % cd)

        neigh_int_ips = [i.ip_address for i in neigh_ints]
        if all_unique(neigh_int_ips):
            log.debug("All interface IP addresses unique for %s" % cd)
            duplicates = duplicate_items(neigh_int_ips)
        else:
            tests_passed = False
            duplicate_ips = set(duplicate_items(neigh_int_ips))
            duplicate_ints = [n for n in neigh_ints
                    if n.ip_address in duplicate_ips]
            duplicates = ", ".join("%s: %s" % (i.node, i.ip_address)
                    for i in duplicate_ints)
            log.warning("Duplicate IP addresses on %s. %s" %
                    (cd, duplicates))

    if tests_passed:
        log.info("All IPv4 tests passed.")
    else:
        log.warning("Some IPv4 tests failed.")

    return tests_passed
