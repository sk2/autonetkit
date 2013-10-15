from autonetkit.compilers.device.server_base import ServerCompiler
import autonetkit.log as log

class UbuntuCompiler(ServerCompiler):

    def compile(self, node):
        super(UbuntuCompiler, self).compile(node)
        # up route add -net ${route.network} gw ${router.gw} dev ${route.interface}
        self.static_routes(node)

    def static_routes(self, node):
        node.static_routes_v4 = [] # initialise for case of no routes -> simplifies template logic
        node.static_routes_v6 = [] # initialise for case of no routes -> simplifies template logic
        if not self.anm['phy'].data.enable_routing:
            log.debug("Routing disabled, not configuring static routes for Ubuntu server %s" % node)
            return

        l3_conn_node = self.anm['l3_conn'].node(node)
        phy_node = self.anm['phy'].node(node)
        gateway_list = [n for n in l3_conn_node.neighbors()
            if n.is_router]
        if not len(gateway_list):
            log.warning("Server %s is not directly connected to any routers" % node)
        else:
            gateway = gateway_list[0] # choose first (and only gateway)
            if len(gateway_list) > 1:
                log.info("Server %s is multi-homed, using gateway %s" % (node, gateway))

        #TODO: warn if server has no neighbors in same ASN (either in design or verification steps)
        #TODO: need to check that servers don't have any direct ebgp connections

        gateway_edge_l3 = self.anm['l3_conn'].edge(node, gateway)
        server_interface = gateway_edge_l3.src_int
        server_interface_id = self.nidb.interface(server_interface).id

        gateway_interface = gateway_edge_l3.dst_int

        gateway_ipv4 = gateway_ipv6 = None
        if node.ip.use_ipv4:
            gateway_ipv4 = gateway_interface['ipv4'].ip_address
        if node.ip.use_ipv6:
            gateway_ipv6 = gateway_interface['ipv6'].ip_address

        #TODO: look at aggregation
        #TODO: catch case of ip addressing being disabled

        #TODO: handle both ipv4 and ipv6

        # IGP advertised infrastructure pool from same AS
        for infra_route in self.anm['ipv4'].data['infra_blocks'][phy_node.asn]:
            node.static_routes_v4.append({
                    "network": infra_route,
                    "gw": gateway_ipv4,
                    "interface": server_interface_id,
                    "description": "Route to infra subnet in local AS %s via %s" % (phy_node.asn, gateway),
                    })

        # eBGP advertised loopbacks in all (same + other) ASes
        for asn, asn_routes in self.anm['ipv4'].data['loopback_blocks'].items():
            for asn_route in asn_routes:
                node.static_routes_v4.append({
                    "network": asn_route,
                    "gw": gateway_ipv4,
                    "interface": server_interface_id,
                    "description": "Route to loopback subnet in AS %s via %s" % (asn, gateway),
                    })


