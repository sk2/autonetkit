#!/usr/bin/python
# -*- coding: utf-8 -*-
from autonetkit.compiler import sort_sessions
from autonetkit.compilers.device.device_base import DeviceCompiler
from autonetkit.nidb import ConfigStanza

import autonetkit.plugins.naming as naming
import autonetkit.log as log
import netaddr
from autonetkit.ank import sn_preflen_to_network


class RouterCompiler(DeviceCompiler):

    """Base router compiler"""

    lo_interface = 'lo0'
    lo_interface_prefix = 'lo'

# and set per platform

    def ibgp_session_data(self, session, ip_version):

        # Don't make staticmethod as may want to extend (DeviceCompiler.g. in
        # IOS compiler for vpnv4)

        node = session.src
        neigh = session.dst

        if ip_version == 4:
            neigh_ip = neigh['ipv4']
            use_ipv4 = True
            use_ipv6 = False
        elif ip_version == 6:
            neigh_ip = neigh['ipv6']
            use_ipv4 = False
            use_ipv6 = True

        # TODO: return ConfigStanza rather than a dict
        data = {  # TODO: this is platform dependent???
            'neighbor': neigh.label,
            'use_ipv4': use_ipv4,
            'use_ipv6': use_ipv6,
            'asn': neigh.asn,
            'loopback': neigh_ip.loopback,
            'update_source': node.loopback_zero.id,
        }
        return data

    def ebgp_session_data(self, session, ip_version):
        node = session.src
        neigh = session.dst
        if ip_version == 4:
            neigh_ip = neigh['ipv4']
            local_int_ip = session.src_int['ipv4'].ip_address
            dst_int_ip = session.dst_int['ipv4'].ip_address
            use_ipv4 = True
            use_ipv6 = False
        elif ip_version == 6:
            neigh_ip = neigh['ipv6']
            local_int_ip = session.src_int['ipv6'].ip_address
            dst_int_ip = session.dst_int['ipv6'].ip_address
            use_ipv4 = False
            use_ipv6 = True

        md5_password = session.md5_password
        multihop = session.multihop

        # TODO: return ConfigStanza rather than a dict
        data = {  # TODO: change templates to access from node.bgp.lo_int
            'neighbor': neigh.label,
            'use_ipv4': use_ipv4,
            'use_ipv6': use_ipv6,
            'asn': neigh.asn,
            'loopback': neigh_ip.loopback,
            'local_int_ip': local_int_ip,
            'dst_int_ip': dst_int_ip,
            'update_source': node.loopback_zero.id,
            'md5_password': md5_password,
            'multihop': multihop,
        }
        return data

    def __init__(self, nidb, anm):
        """Base Router compiler"""

        super(RouterCompiler, self).__init__(nidb, anm)

    def compile(self, node):
        node.do_render = True  # turn on rendering

        phy_node = self.anm['phy'].node(node)
        ipv4_node = self.anm['ipv4'].node(node)

        node.global_custom_config = phy_node.custom_config

        node.add_stanza("ip")
        node.ip.use_ipv4 = phy_node.use_ipv4 or False
        node.ip.use_ipv6 = phy_node.use_ipv6 or False
        if not (node.ip.use_ipv4 and node.ip.use_ipv6):
            node.log.debug(
                'Neither IPv4 nor IPv6 specified: using default IPv4')

        self.static_routes(node)

        # node.ip.use_ipv4 = True

        node.label = naming.network_hostname(phy_node)
        node.input_label = phy_node.id
        if node.ip.use_ipv4:
            node.loopback = ipv4_node.loopback
            node.loopback_subnet = netaddr.IPNetwork(node.loopback)
            node.loopback_subnet.prefixlen = 32

        if self.anm['phy'].data.enable_routing:
            # applies even if ipv4 disabled, used for eg eigrp, bgp, ...
            node.router_id = ipv4_node.loopback

        self.interfaces(node)
        if self.anm.has_overlay('ospf') and node in self.anm['ospf']:
            self.ospf(node)
        if self.anm.has_overlay('isis') and node in self.anm['isis']:
            self.isis(node)
        if self.anm.has_overlay('eigrp') and node in self.anm['eigrp']:
            self.eigrp(node)
        # TODO: drop bgp overlay
        bgp_overlays = ["bgp", "ebgp_v4", "ibgp_v4", "ebgp_v6", "ibgp_v6"]
        use_bgp = False
        for overlay in bgp_overlays:
            if (self.anm.has_overlay(overlay)
                        and node in self.anm[overlay]
                        and self.anm[overlay].node(node).degree() > 0
                    ):
                use_bgp = True
                break

        if use_bgp:
            self.bgp(node)

    def static_routes(self, node):
        node.ipv4_static_routes = []
        if self.anm.has_overlay("ipv4"):
            ipv4_node = self.anm['ipv4'].node(node)
            if ipv4_node and ipv4_node.static_routes:
                for route in ipv4_node.static_routes:
                    stanza = ConfigStanza(
                        prefix=route.prefix,
                        netmask=route.netmask,
                        nexthop=route.nexthop,
                        metric=route.metric,
                    )
                    node.ipv4_static_routes.append(stanza)

        node.ipv6_static_routes = []
        if self.anm.has_overlay("ipv6"):
            ipv6_node = self.anm['ipv6'].node(node)
            if ipv6_node and ipv6_node.static_routes:
                for route in ipv6_node.static_routes:
                    stanza = ConfigStanza(
                        prefix=route.prefix,
                        nexthop=route.nexthop,
                        metric=route.metric,
                    )
                    node.ipv6_static_routes.append(stanza)

    def interfaces(self, node):
        node.interfaces = []

        node.loopback_zero.id = self.lo_interface
        node.loopback_zero.description = 'Loopback'
        phy_node = self.anm['phy'].node(node)
        node.loopback_zero.custom_config = phy_node.loopback_zero.custom_config

        if node.ip.use_ipv4:
            ipv4_node = self.anm['ipv4'].node(node)
            node.loopback_zero.ipv4_address = ipv4_node.loopback
            node.loopback_zero.ipv4_subnet = node.loopback_subnet

        # TODO: bne consistent wit hcidr name so can use in cisco ios xr templates
        # if node.ip.use_ipv6:
            #ipv6_node = self.anm['ipv6'].node(node)
            #node.loopback_zero.ipv6_address = ipv6_node.loopback
            #node.loopback_zero.ipv6_subnet = node.loopback_subnet

        for interface in node.physical_interfaces():
            phy_int = self.anm['phy'].interface(interface)
            interface.physical = True

            # TODO: allocate ID in platform compiler

            if not phy_int:
                # for instance if added as management interface to nidb in
                # compile
                continue

            interface.custom_config = phy_int.custom_config

            interface.description = phy_int.description

            continue

    def ospf(self, node):
        """Returns OSPF links, also sets process_id
        """

        g_ospf = self.anm['ospf']
        g_ipv4 = self.anm['ipv4']
        ospf_node = g_ospf.node(node)
        ospf_stanza = node.add_stanza("ospf")

        ospf_stanza.custom_config = ospf_node.custom_config

        # default, inherited enable if necessary
        node.ospf.ipv4_mpls_te = False

        node.ospf.loopback_area = g_ospf.node(node).area or 0

        node.ospf.process_id = ospf_node.process_id
        node.ospf.lo_interface = self.lo_interface

        node.ospf.ospf_links = []

        # aggregate by area
        from collections import defaultdict
        interfaces_by_area = defaultdict(list)

        for interface in node.physical_interfaces():
            if interface.exclude_igp:
                continue  # don't configure IGP for this interface

            ospf_int = g_ospf.interface(interface)
            if ospf_int and ospf_int.is_bound:
                area = ospf_int.area
                # TODO: can we remove the next line?
                area = str(area)  # can't serialize IPAddress object to JSON
                # TODO: put in interface rather than interface.id for
                # consistency
                try:
                    cost = int(ospf_int.cost)
                except TypeError:
                    #TODO: log warning here
                    cost = 1
                stanza = ConfigStanza(id=interface.id,
                                      cost=cost, passive=False)

                if node.ip.use_ipv4:
                    stanza.ipv4_address = ospf_int['ipv4'].ip_address
                    stanza.ipv4_subnet = ospf_int['ipv4'].subnet
                if node.ip.use_ipv6:
                    stanza.ipv6_address = ospf_int['ipv6'].ip_address
                    stanza.ipv6_subnet = ospf_int['ipv6'].subnet

                interfaces_by_area[area].append(stanza)

        loopback_zero = node.loopback_zero
        ospf_loopback_zero = g_ospf.interface(loopback_zero)
        router_area = ospf_loopback_zero.area  # area assigned to router
        # can't serialize IPAddress object to JSON
        router_area = str(router_area)
        stanza = ConfigStanza(id=node.loopback_zero.id,
                              cost=0, passive=True)
        interfaces_by_area[router_area].append(stanza)

        node.ospf.interfaces_by_area = ConfigStanza(**interfaces_by_area)

        # TODO: split this into a generic IGP function
        added_networks = set()
        for interface in node.physical_interfaces():
            if interface.exclude_igp:
                continue  # don't configure IGP for this interface
            if not interface.use_ipv4:
                continue
            ipv4_int = g_ipv4.interface(interface)
            ospf_int = g_ospf.interface(interface)
            if not ospf_int.is_bound:
                continue  # not an OSPF interface
            try:
                ospf_cost = int(ospf_int.cost)
            except TypeError:
                try:
                    ospf_cost = netaddr.IPAddress(ospf_int.cost)
                except (TypeError, netaddr.AddrFormatError):
                    log.debug('Using default OSPF cost of 1 for %s on %s',
                              ospf_int, node)
                    ospf_cost = 1  # default
            interface.ospf_cost = ospf_cost
            network = ipv4_int.subnet

            #TODO: refactor to allow injecting loopback IPs, etc into IGP
            if ospf_int and ospf_int.is_bound and network \
                    not in added_networks:  # don't add more than once
                added_networks.add(network)
                link_stanza = ConfigStanza(
                    network=network, interface=interface, area=ospf_int.area)
                node.ospf.ospf_links.append(link_stanza)

        for interface in node.loopback_interfaces():
            phy_int = self.anm['phy'].interface(interface)
            ipv4_int = g_ipv4.interface(interface)
            if not phy_int.inject_to_igp:
                #TODO: need to confirm which area to use
                continue

            network = ipv4_int.subnet
            if network in added_networks:
                #TODO: may want to warn here
                continue # already advertised ("how? - warn if so!)

            # Use the same area as Loopback Zero
            area = node.ospf.loopback_area

            if not network:
                log.info("Not injecting unset network on loopback %s "
                    "to IGP", interface)
                continue

            link_stanza = ConfigStanza(
             network=network, interface=interface, area=area)
            node.ospf.ospf_links.append(link_stanza)

            # also add networks for subnets to servers in the same AS

    def bgp(self, node):
        phy_node = self.anm['phy'].node(node)
        g_ipv4 = self.anm['ipv4']
        if node.ip.use_ipv6:
            g_ipv6 = self.anm['ipv6']
        asn = phy_node.asn
        node.asn = asn
        bgp_stanza = node.add_stanza("bgp")
        if self.anm.has_overlay("bgp"):
            bgp_stanza.custom_config = phy_node['bgp'].custom_config
        else:
            bgp_stanza.custom_config = ""

        node.bgp.ipv4_advertise_subnets = []
        if node.ip.use_ipv4:
            node.bgp.ipv4_advertise_subnets = \
                g_ipv4.data.infra_blocks.get(
                    asn) or []  # could be none (one-node AS) default empty list
        node.bgp.ipv6_advertise_subnets = []
        if node.ip.use_ipv6:
            g_ipv6 = self.anm['ipv6']
            node.bgp.ipv6_advertise_subnets = \
                g_ipv6.data.infra_blocks.get(asn) or []

        ibgp_neighbors = []
        ibgp_rr_clients = []
        ibgp_rr_parents = []

        g_ibgp_v4 = self.anm['ibgp_v4']
        for session in sort_sessions(g_ibgp_v4.edges(phy_node)):
            if session.exclude:
                log.debug('Skipping excluded ibgp session %s', session)
                # exclude from regular ibgp config (eg VRF, VPLS, etc)
                continue

            data = self.ibgp_session_data(session, ip_version=4)
            bgp_stanza = ConfigStanza(**data)

            direction = session.direction
            if direction == 'down':
                ibgp_rr_clients.append(bgp_stanza)
            elif direction == 'up':
                ibgp_rr_parents.append(bgp_stanza)
            else:
                ibgp_neighbors.append(bgp_stanza)

        # TODO: check v6 hierarchy only created if node set to being v4 or v6

        if node.ip.use_ipv6:
            g_ibgp_v6 = self.anm['ibgp_v6']
            for session in sort_sessions(g_ibgp_v6.edges(phy_node)):
                if session.exclude:
                    log.debug('Skipping excluded ibgp session %s', session)
                    # exclude from regular ibgp config (eg VRF, VPLS, etc)
                    continue
                data = self.ibgp_session_data(session, ip_version=6)
                bgp_stanza = ConfigStanza(**data)

                direction = session.direction
                if direction == 'down':
                    ibgp_rr_clients.append(bgp_stanza)
                elif direction == 'up':
                    ibgp_rr_parents.append(bgp_stanza)
                else:
                    ibgp_neighbors.append(bgp_stanza)

        # TODO: update this to use ibgp_v4 and ibgp_v6 overlays

        node.bgp.ibgp_neighbors = ibgp_neighbors
        node.bgp.ibgp_rr_clients = ibgp_rr_clients
        node.bgp.ibgp_rr_parents = ibgp_rr_parents

        # ebgp

        ebgp_neighbors = []
        g_ebgp_v4 = self.anm['ebgp_v4']
        for session in sort_sessions(g_ebgp_v4.edges(phy_node)):
            if session.exclude:
                log.debug('Skipping excluded ebgp session %s', session)
                # exclude from regular ibgp config (eg VRF, VPLS, etc)
                continue
            data = self.ebgp_session_data(session, ip_version=4)
            bgp_stanza = ConfigStanza(**data)
            ebgp_neighbors.append(bgp_stanza)

        if node.ip.use_ipv6:
            g_ebgp_v6 = self.anm['ebgp_v6']
            for session in sort_sessions(g_ebgp_v6.edges(phy_node)):
                if session.exclude:
                    log.debug('Skipping excluded ebgp session %s', session)
                    # exclude from regular ibgp config (eg VRF, VPLS, etc)
                    continue
                data = self.ebgp_session_data(session, ip_version=6)
                bgp_stanza = ConfigStanza(**data)
                ebgp_neighbors.append(bgp_stanza)

        ebgp_neighbors = sorted(ebgp_neighbors, key=lambda x: x.asn)
        node.bgp.ebgp_neighbors = ebgp_neighbors

        return

    def eigrp(self, node):

        g_eigrp = self.anm['eigrp']
        g_ipv4 = self.anm['ipv4']
        eigrp_node = self.anm['eigrp'].node(node)
        node.eigrp.process_id = eigrp_node.process_id
        node.eigrp.custom_config = eigrp_node.custom_config

        ipv4_networks = set()
        for interface in node.physical_interfaces():
            if interface.exclude_igp:
                continue  # don't configure IGP for this interface
            ipv4_int = g_ipv4.interface(interface)
            eigrp_int = g_eigrp.interface(interface)
            if not eigrp_int.is_bound:
                continue  # not an EIGRP interface
            network = ipv4_int.subnet
            if eigrp_int and eigrp_int.is_bound and interface.use_ipv4:
                ipv4_networks.add(network)

        # Loopback zero subnet

        ipv4_networks.add(node.loopback_zero.ipv4_cidr)

        node.eigrp.ipv4_networks = sorted(list(ipv4_networks))

    def isis(self, node):
        g_isis = self.anm['isis']
        isis_node = g_isis.node(node)
        process_id = isis_node.process_id
        node.isis.custom_config = isis_node.custom_config

        # default, inherited enable if necessary
        node.isis.ipv4_mpls_te = False

        for interface in node.physical_interfaces():
            if interface.exclude_igp:
                continue  # don't configure IGP for this interface

            phy_int = self.anm['phy'].interface(interface)

            isis_int = phy_int['isis']
            if isis_int and isis_int.is_bound:
                isis_node = g_isis.node(node)
                interface.isis = {
                    'metric': isis_int.metric,
                    'process_id': process_id,
                    'use_ipv4': node.ip.use_ipv4,
                    'use_ipv6': node.ip.use_ipv6,
                    'multipoint': isis_int.multipoint,
                }

                # TODO: add wrapper for this

        g_isis = self.anm['isis']
        isis_node = self.anm['isis'].node(node)
        node.isis.net = isis_node.net

        # TODO: generalise loopbacks to allow more than one per device

        node.isis.process_id = process_id
        node.isis.lo_interface = self.lo_interface

# set isis on loopback_zero

        node.loopback_zero.isis = {'use_ipv4': node.ip.use_ipv4,
                                   'use_ipv6': node.ip.use_ipv6}

        # TODO: add wrapper for this
