#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.log as log
from autonetkit.compilers.device.server_base import ServerCompiler


class UbuntuCompiler(ServerCompiler):

    def compile(self, node):
        super(UbuntuCompiler, self).compile(node)

        # up route add -net ${route.network} gw ${router.gw} dev ${route.interface}

        self.static_routes(node)

    def static_routes(self, node):
        node.static_routes_v4 = []  # initialise for case of no routes -> simplifies template logic
        node.host_routes_v4 = []  # initialise for case of no routes -> simplifies template logic
        node.static_routes_v6 = []  # initialise for case of no routes -> simplifies template logic
        node.host_routes_v6 = []  # initialise for case of no routes -> simplifies template logic
        if not self.anm['phy'].data.enable_routing:
            log.info('Routing disabled, not configuring static routes for Ubuntu server %s'
                      % node)
            return

        if self.anm['phy'].node(node).dont_configure_static_routing:
            log.info('Static routing disabled for server %s' % node)
            return

        l3_conn_node = self.anm['l3_conn'].node(node)
        phy_node = self.anm['phy'].node(node)
        gateway_list = [n for n in l3_conn_node.neighbors()
                        if n.is_router]
        if not len(gateway_list):
            log.warning('Server %s is not directly connected to any routers'
                         % node)
            return
        else:
            gateway = gateway_list[0]  # choose first (and only gateway)
            if len(gateway_list) > 1:
                log.info('Server %s is multi-homed, using gateway %s'
                         % (node, gateway))

        # TODO: warn if server has no neighbors in same ASN (either in design or verification steps)
        # TODO: need to check that servers don't have any direct ebgp connections

        gateway_edge_l3 = self.anm['l3_conn'].edge(node, gateway)
        server_interface = gateway_edge_l3.src_int
        server_interface_id = self.nidb.interface(server_interface).id

        gateway_interface = gateway_edge_l3.dst_int

        gateway_ipv4 = gateway_ipv6 = None
        if node.ip.use_ipv4:
            gateway_ipv4 = gateway_interface['ipv4'].ip_address
        if node.ip.use_ipv6:
            gateway_ipv6 = gateway_interface['ipv6'].ip_address

        # TODO: look at aggregation
        # TODO: catch case of ip addressing being disabled

        # TODO: handle both ipv4 and ipv6

        # IGP advertised infrastructure pool from same AS

        for infra_route in self.anm['ipv4'].data['infra_blocks'
                ][phy_node.asn]:

           # host_routes_v4

            route_entry = {
                'network': infra_route,
                'prefix': infra_route.network,
                'gw': gateway_ipv4,
                'interface': server_interface_id,
                'description': 'Route to infra subnet in local AS %s via %s' \
                    % (phy_node.asn, gateway),
                }
            if infra_route.prefixlen == 32:
                node.host_routes_v4.append(route_entry)
            else:
                node.static_routes_v4.append(route_entry)

        # eBGP advertised loopbacks in all (same + other) ASes

        for (asn, asn_routes) in self.anm['ipv4'].data['loopback_blocks'
                ].items():
            for asn_route in asn_routes:
                route_entry = {
                    'network': asn_route,
                    'prefix': asn_route.network,
                    'gw': gateway_ipv4,
                    'interface': server_interface_id,
                    'description': 'Route to loopback subnet in AS %s via %s' \
                        % (asn, gateway),
                    }
                if asn_route.prefixlen == 32:
                    node.host_routes_v4.append(route_entry)
                else:
                    node.static_routes_v4.append(route_entry)

        # TODO: combine the above logic into single step rather than creating dict then formatting with it

        cloud_init_static_routes = []
        for entry in node.static_routes_v4:
            formatted = 'route add -net %s gw %s dev %s' \
                % (entry.network, entry.gw, entry.interface)
            cloud_init_static_routes.append(formatted)
        for entry in node.host_routes_v4:
            formatted = 'route add -host %s gw %s dev %s' \
                % (entry.prefix, entry.gw, entry.interface)
            cloud_init_static_routes.append(formatted)

        node.cloud_init.static_routes = cloud_init_static_routes


        # Render inline for packaging into yaml
        # TODO: no longer used, but keep as reference for later templates that require this format
        # import autonetkit.render
        # import os
        # lookup = autonetkit.render.initialise_lookup()
        # render_template = os.path.join("templates", "linux", "static_route.mako")
        # render_output = autonetkit.render.render_inline(node, render_template)
        # node.cloud_init.static_routes = render_output
