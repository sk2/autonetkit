import autonetkit.log as log


class PlatformCompiler(object):

    """Base Platform Compiler"""

    def __init__(self, nidb, anm, host):
        self.nidb = nidb
        self.anm = anm
        self.host = host

    @property
    def timestamp(self):
        return self.nidb.timestamp

    def compile(self):
        # TODO: make this abstract
        pass

    def copy_across_ip_addresses(self):
        # log.info("Copying IP addresses to device model")
        # TODO: try/except and raise SystemError as fatal error if cant copy
        from autonetkit.ank import sn_preflen_to_network

        # TODO:  check if this will clobber with platform?
        for node in self.nidb.l3devices(host=self.host):
            phy_node = self.anm['phy'].node(node)

            node.add_stanza("ip")
            node.ip.use_ipv4 = phy_node.use_ipv4 or False
            node.ip.use_ipv6 = phy_node.use_ipv6 or False

            for interface in node.interfaces:
                phy_int = phy_node.interface(interface)
                if phy_int.exclude_igp is not None:
                    interface.exclude_igp = phy_int.exclude_igp

                if phy_node.use_ipv4:
                    ipv4_int = phy_int['ipv4']

                    """
                    TODO: refactor this logic (and for ipv6) to only check if None
                    then compilers are more pythonic - test for IP is None
                    rather than bound etc - simplifies logic
                    make try to copy, and if fail then warn and set use_ipv4 to False
                    """
                    if node.is_server() and interface.is_loopback:
                        continue
                    if interface.is_physical and not interface.is_bound:
                        continue

                    # permit unbound ip interfaces (e.g. if skipped for l2 encap)
                    if interface.is_physical and not ipv4_int.is_bound:
                        interface.use_ipv4 = False
                        continue

                    if ipv4_int.ip_address is None:
                        #TODO: put into dev log
                        log.debug("No IP address allocated on %s", interface)
                        interface.use_ipv4 = False
                        continue

                    # TODO: also need to skip layer2 virtual interfaces
                    # interface is connected
                    try:
                        interface.ipv4_address = ipv4_int.ip_address
                        interface.ipv4_subnet = ipv4_int.subnet
                        interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                                                                    interface.ipv4_subnet.prefixlen)
                    except AttributeError, error:
                        log.warning(
                            "Unable to copy across IPv4 for %s" % interface)
                        log.debug(error)
                    else:
                        interface.use_ipv4 = True
                if phy_node.use_ipv6:
                    ipv6_int = phy_int['ipv6']
                    if node.is_server() and interface.is_loopback:
                        continue
                    if interface.is_physical and not interface.is_bound:
                        continue
                    # permit unbound ip interfaces (e.g. if skipped for l2 encap)
                    if interface.is_physical and not ipv6_int.is_bound:
                        interface.use_ipv6 = False
                        continue
                    if ipv6_int.ip_address is None:
                        #TODO: put into dev log
                        log.debug("No IP address allocated on %s", interface)
                        interface.use_ipv6 = False
                        continue
                    try:
                        # TODO: copy ip address as well
                        interface.ipv6_subnet = ipv6_int.subnet
                        interface.ipv6_address = sn_preflen_to_network(ipv6_int.ip_address,
                                                                       interface.ipv6_subnet.prefixlen)
                    except AttributeError:
                        log.warning(
                            "Unable to copy IPv6 subnet for %s" % interface)
                    else:
                        interface.use_ipv6 = True
