from autonetkit.compilers.device.router_base import RouterCompiler

class QuaggaCompiler(RouterCompiler):
    """Base Quagga compiler"""
    lo_interface = "lo0:1"

    def compile(self, node):
        super(QuaggaCompiler, self).compile(node)


    def interfaces(self, node):
        """Quagga interface compiler"""
        ipv4_node = self.anm['ipv4'].node(node)
        phy_node = self.anm['phy'].node(node)

        super(QuaggaCompiler, self).interfaces(node)
        # OSPF cost

        if phy_node.is_l3device:
            node.loopback_zero.id = self.lo_interface
            node.loopback_zero.description = "Loopback"
            node.loopback_zero.ipv4_address = ipv4_node.loopback
            node.loopback_zero.ipv4_subnet = node.loopback_subnet

    def ospf(self, node):
        """Quagga ospf compiler"""
        super(QuaggaCompiler, self).ospf(node)

        # add eBGP link subnets
        node.ospf.passive_interfaces = []

        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface

            bgp_int = self.anm['bgp'].interface(interface)
            if bgp_int.ebgp: # ebgp interface
                node.ospf.passive_interfaces.append(
                        id=interface.id,
                        )
                subnet = bgp_int['ipv4'].subnet
                default_ebgp_area = 0
                node.ospf.ospf_links.append(
                        network=subnet,
                        area=default_ebgp_area,
                        )

    def isis(self, node):
        """Sets ISIS links
        """
        g_isis = self.anm['isis']
        isis_node = g_isis.node(node)
        node.isis.net = isis_node.net
        node.isis.process_id = isis_node.process_id

