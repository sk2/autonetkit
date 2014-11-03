#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.log as log
from autonetkit.compilers.device.server_base import ServerCompiler
from autonetkit.nidb import ConfigStanza


class UbuntuCompiler(ServerCompiler):

    def compile(self, node):
        super(UbuntuCompiler, self).compile(node)

        # up route add -net ${route.network} gw ${router.gw} dev
        # ${route.interface}

        self.static_routes(node)

    def static_routes(self, node):
        # initialise for case of no routes -> simplifies template logic
        node.static_routes_v4 = []
        # initialise for case of no routes -> simplifies template logic
        node.host_routes_v4 = []
        # initialise for case of no routes -> simplifies template logic
        node.static_routes_v6 = []
        # initialise for case of no routes -> simplifies template logic
        node.host_routes_v6 = []
        if not self.anm['phy'].data.enable_routing:
            log.info('Routing disabled, not configuring static routes for Ubuntu server %s'
                     % node)
            return

        if self.anm['phy'].node(node).dont_configure_static_routing:
            log.info('Static routing disabled for server %s' % node)
            return

        l3_node = self.anm['layer3'].node(node)
        gateway_list = [n for n in l3_node.neighbors()
                        if n.is_router()]
        if not len(gateway_list):
            log.warning('Server %s is not directly connected to any routers'
                        % node)
            return
        elif len(gateway_list) > 1:
            log.info('Server %s is multi-homed: using gateways %s'
                     % (node, sorted(gateway_list)))

        # TODO: warn if server has no neighbors in same ASN (either in design or verification steps)
        # TODO: need to check that servers don't have any direct ebgp
        # connections

        cloud_init_static_routes = []
        g_l3 = self.anm['layer3']

        for gateway in sorted(gateway_list):
            for gateway_edge_l3 in g_l3.edges(node, gateway):
                server_interface = gateway_edge_l3.src_int
                server_interface_id = self.nidb.interface(server_interface).id

                gateway_interface = gateway_edge_l3.dst_int

                gateway_ipv4 = gateway_ipv6 = None
                node.add_stanza("ip")
                if node.ip.use_ipv4:
                    gateway_ipv4 = gateway_interface['ipv4'].ip_address
                if node.ip.use_ipv6:
                    gateway_ipv6 = gateway_interface['ipv6'].ip_address

                # TODO: look at aggregation
                # TODO: catch case of ip addressing being disabled

                # TODO: handle both ipv4 and ipv6

                # IGP advertised infrastructure pool from same AS
                static_routes_v4 = []
                host_routes_v4 = []
                for (asn, asn_routes) in self.anm['ipv4'].data['infra_blocks'].items():

                    # host_routes_v4
                    for infra_route in asn_routes:
                        route_entry = {
                            'network': infra_route,
                            'prefix': infra_route.network,
                            'gw': gateway_ipv4,
                            'interface': server_interface_id,
                            'description': 'Route to infra subnet in AS %s via %s'
                            % (asn, gateway),
                        }
                        route_entry = ConfigStanza(**route_entry)
                        if infra_route.prefixlen == 32:
                            host_routes_v4.append(route_entry)
                        else:
                            static_routes_v4.append(route_entry)

                # eBGP advertised loopbacks in all (same + other) ASes

                for (asn, asn_routes) in self.anm['ipv4'].data['loopback_blocks'
                                                               ].items():
                    for asn_route in asn_routes:
                        route_entry = {
                            'network': asn_route,
                            'prefix': asn_route.network,
                            'gw': gateway_ipv4,
                            'interface': server_interface_id,
                            'description': 'Route to loopback subnet in AS %s via %s'
                            % (asn, gateway),
                        }
                        route_entry = ConfigStanza(**route_entry)
                        if asn_route.prefixlen == 32:
                            host_routes_v4.append(route_entry)
                        else:
                            static_routes_v4.append(route_entry)

                # TODO: combine the above logic into single step rather than
                # creating dict then formatting with it

                for entry in static_routes_v4:
                    formatted = 'route add -net %s gw %s dev %s' \
                        % (entry.network, entry.gw, entry.interface)
                    cloud_init_static_routes.append(formatted)
                for entry in host_routes_v4:
                    formatted = 'route add -host %s gw %s dev %s' \
                        % (entry.prefix, entry.gw, entry.interface)
                    cloud_init_static_routes.append(formatted)

        node.add_stanza("cloud_init")
        node.cloud_init.static_routes = cloud_init_static_routes

        # Render inline for packaging into yaml
        # TODO: no longer used, but keep as reference for later templates that require this format
        # import autonetkit.render
        # import os
        # lookup = autonetkit.render.initialise_lookup()
        # render_template = os.path.join("templates", "linux", "static_route.mako")
        # render_output = autonetkit.render.render_inline(node, render_template)
        # node.cloud_init.static_routes = render_output
