import autonetkit.log as log

class PlatformCompiler(object):
    """Base Platform Compiler"""
# and set properties in nidb._graph.graph
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
        #TODO: try/except and raise SystemError as fatal error if cant copy
        from autonetkit.ank import sn_preflen_to_network

        #TODO:  check if this will clobber with platform?
        for node in self.nidb.l3devices(host=self.host):
            phy_node = self.anm['phy'].node(node)

            node.add_stanza("ip")
            node.ip.use_ipv4 = phy_node.use_ipv4 or False
            node.ip.use_ipv6 = phy_node.use_ipv6 or False

            for interface in node.interfaces:
                phy_int = phy_node.interface(interface)
                if phy_node.use_ipv4:
                    ipv4_int = phy_int['ipv4']
                    if node.is_server() and interface.is_loopback:
                        continue
                    if interface.is_physical and not interface.is_bound:
                        continue
                    # interface is connected
                    interface.use_ipv4 = True
                    interface.ipv4_address = ipv4_int.ip_address
                    interface.ipv4_subnet = ipv4_int.subnet
                    interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                            interface.ipv4_subnet.prefixlen)
                if phy_node.use_ipv6:
                    ipv6_int = phy_int['ipv6']
                    if node.is_server() and interface.is_loopback:
                        continue
                    if interface.is_physical and not interface.is_bound:
                        continue
                    interface.use_ipv6 = True
                    try:
                        #TODO: copy ip address as well
                        interface.ipv6_subnet = ipv6_int.subnet
                        interface.ipv6_address = sn_preflen_to_network(ipv6_int.ip_address,
                            interface.ipv6_subnet.prefixlen)
                    except AttributeError:
                        log.warning("Unable to copy IPv6 subnet for %s" % interface)

