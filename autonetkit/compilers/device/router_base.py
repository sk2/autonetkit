from autonetkit.compiler import sort_sessions
import autonetkit.plugins.naming as naming
import autonetkit.log as log
import netaddr
from autonetkit.ank import sn_preflen_to_network

class RouterCompiler(object):
    """Base router compiler"""
    lo_interface = "lo0"
    lo_interface_prefix = "lo"
# and set per platform

    def ibgp_session_data(self, session, ip_version):
        # Don't make staticmethod as may want to extend (e.g. in IOS compiler for vpnv4)
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

        data = {
            'neighbor': neigh.label,
            'use_ipv4': use_ipv4,
            'use_ipv6': use_ipv6,
            'asn': neigh.asn,
            'loopback': neigh_ip.loopback,
            # TODO: this is platform dependent???
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

        data = {
            'neighbor': neigh.label,
            'use_ipv4': use_ipv4,
            'use_ipv6': use_ipv6,
            'asn': neigh.asn,
            'loopback': neigh_ip.loopback,
            'local_int_ip': local_int_ip,
            'dst_int_ip': dst_int_ip,
            # TODO: change templates to access from node.bgp.lo_int
            'update_source': node.loopback_zero.id,
            }
        return data

    def __init__(self, nidb, anm):
        """Base Router compiler"""
        self.nidb = nidb
        self.anm = anm

    def compile(self, node):
        phy_node = self.anm['phy'].node(node)
        ipv4_node = self.anm['ipv4'].node(node)

        node.ip.use_ipv4 = phy_node.use_ipv4 or False
        node.ip.use_ipv6 = phy_node.use_ipv6 or False
        if not (node.ip.use_ipv4 and node.ip.use_ipv6):
            log.debug("Neither IPv4 nor IPv6 specified for %s, using IPv4" % node)
            #node.ip.use_ipv4 = True

        node.label = naming.network_hostname(phy_node)
        node.input_label = phy_node.id
        if node.ip.use_ipv4:
            node.loopback = ipv4_node.loopback
            node.loopback_subnet = netaddr.IPNetwork(node.loopback)
            node.loopback_subnet.prefixlen = 32

        if self.anm['phy'].data.enable_routing:
            node.router_id = ipv4_node.loopback # applies even if ipv4 disabled, used for eg eigrp, bgp, ...

        self.interfaces(node)
        if self.anm.has_overlay("ospf") and node in self.anm['ospf']:
            self.ospf(node)
        if self.anm.has_overlay("isis") and node in self.anm['isis']:
            self.isis(node)
        if self.anm.has_overlay("eigrp") and node in self.anm['eigrp']:
            self.eigrp(node)
        if self.anm.has_overlay("bgp") and node in self.anm['bgp']:
            self.bgp(node)

    def interfaces(self, node):
        node.interfaces = []

        node.loopback_zero.id = self.lo_interface
        node.loopback_zero.description = "Loopback"

        for interface in node.physical_interfaces:
            phy_int = self.anm['phy'].interface(interface)
            interface.physical = True
            #TODO: allocate ID in platform compiler

            if not phy_int:
                # for instance if added as management interface to nidb in compile
                continue

            interface.description = phy_int.description
            remote_edges = phy_int.edges()
            if len(remote_edges):
                interface.description = "to %s" % remote_edges[0].dst.label

            #TODO: fix the description to use mapped label
            if node.ip.use_ipv4:
                ipv4_int = phy_int['ipv4']
                if ipv4_int.is_bound:
                    # interface is connected
                    interface.use_ipv4 = True
                    interface.ipv4_address = ipv4_int.ip_address
                    interface.ipv4_subnet = ipv4_int.subnet
                    interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                            interface.ipv4_subnet.prefixlen)

            if node.ip.use_ipv6:
                ipv6_int = phy_int['ipv6']
                if ipv6_int.is_bound:
                    # interface is connected
                    interface.use_ipv6 = True
#TODO: for consistency, make ipv6_cidr
                    interface.ipv6_subnet = ipv6_int.subnet
                    interface.ipv6_address = sn_preflen_to_network(ipv6_int.ip_address,
                            interface.ipv6_subnet.prefixlen)

        for interface in node.loopback_interfaces:
            #TODO: check if nonzero is different to __eq__
            if interface == node.loopback_zero:
                continue
            else:
                phy_int = self.anm['phy'].interface(interface)
                if node.ip.use_ipv4:
                    ipv4_int = phy_int['ipv4']
                    interface.use_ipv4 = True

                    interface.ipv4_address = ipv4_int.loopback
                    interface.ipv4_subnet = node.loopback_subnet
                    interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                            interface.ipv4_subnet.prefixlen)

                if node.ip.use_ipv6:
                    ipv6_int = phy_int['ipv6']
                    interface.use_ipv6 = True
#TODO: for consistency, make ipv6_cidr
                    #interface.ipv6_subnet = ipv6_int.loopback # TODO: do we need for consistency?
                    interface.ipv6_address = sn_preflen_to_network(
                            ipv6_int.loopback, 128)

                # secondary loopbacks
                #TODO: check why vrf names not showing up for all
                #print vrf_interface.vrf_name
            continue

    def ospf(self, node):
        """Returns OSPF links, also sets process_id
        """
        g_ospf = self.anm['ospf']
        g_ipv4 = self.anm['ipv4']

        node.ospf.loopback_area = g_ospf.node(node).area

        node.ospf.process_id = 1 #TODO: set this in build_network module
        node.ospf.lo_interface = self.lo_interface

        node.ospf.ospf_links = []
        added_networks = set()
        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface
            ipv4_int = g_ipv4.interface(interface)
            ospf_int = g_ospf.interface(interface)
            if not ospf_int.is_bound:
                continue # not an OSPF interface
            try:
                ospf_cost = int(ospf_int.cost)
            except TypeError:
                try:
                    ospf_cost = netaddr.IPAddress(ospf_int.cost)
                except TypeError:
                    log.debug("Using default OSPF cost of 1 for %s on %s" % (ospf_int, node))
                    ospf_cost = 1 # default
            interface.ospf_cost = ospf_cost
            network = ipv4_int.subnet
            if (ospf_int and ospf_int.is_bound
                    and network not in added_networks):  # don't add more than once
                added_networks.add(network)
                node.ospf.ospf_links.append(
                    network=network,
                    area=ospf_int.area,
                )

            # also add networks for subnets to servers in the same AS

    def bgp(self, node):
        phy_node = self.anm['phy'].node(node)
        g_bgp = self.anm['bgp']
        g_ipv4 = self.anm['ipv4']
        g_ipv6 = self.anm['ipv6']
        asn = phy_node.asn
        node.asn = asn
        node.bgp.ipv4_advertise_subnets = []
        if node.ip.use_ipv4:
            node.bgp.ipv4_advertise_subnets = g_ipv4.data.infra_blocks.get(
                asn) or []  # could be none (if one-node AS) default empty list
        node.bgp.ipv6_advertise_subnets = []
        if node.ip.use_ipv6:
            g_ipv6 = self.anm['ipv6']
            node.bgp.ipv6_advertise_subnets = g_ipv6.data.infra_blocks.get(
                asn) or []

        ibgp_neighbors = []
        ibgp_rr_clients = []
        ibgp_rr_parents = []

        g_ibgp_v4 = self.anm['ibgp_v4']
        for session in sort_sessions(g_ibgp_v4.edges(phy_node)):
            if session.exclude:
                log.debug("Skipping excluded ibgp session %s" % session)
                continue # exclude from regular ibgp config (eg VRF, VPLS, etc)

            data = self.ibgp_session_data(session, ip_version = 4)

            direction = session.direction
            if direction == 'down':
                ibgp_rr_clients.append(data)
            elif direction == 'up':
                ibgp_rr_parents.append(data)
            else:
                ibgp_neighbors.append(data)

        #TODO: check v6 hierarchy only created if node set to being v4 or v6
        g_ibgp_v6 = self.anm['ibgp_v6']
        for session in sort_sessions(g_ibgp_v6.edges(phy_node)):
            if session.exclude:
                log.debug("Skipping excluded ibgp session %s" % session)
                continue # exclude from regular ibgp config (eg VRF, VPLS, etc)
            data = self.ibgp_session_data(session, ip_version = 6)

            direction = session.direction
            if direction == 'down':
                ibgp_rr_clients.append(data)
            elif direction == 'up':
                ibgp_rr_parents.append(data)
            else:
                ibgp_neighbors.append(data)

        #TODO: update this to use ibgp_v4 and ibgp_v6 overlays

        node.bgp.ibgp_neighbors = ibgp_neighbors
        node.bgp.ibgp_rr_clients = ibgp_rr_clients
        node.bgp.ibgp_rr_parents = ibgp_rr_parents

        #ebgp

        ebgp_neighbors = []
        g_ebgp_v4 = self.anm['ebgp_v4']
        for session in sort_sessions(g_ebgp_v4.edges(phy_node)):
            if session.exclude:
                log.debug("Skipping excluded ebgp session %s" % session)
                continue # exclude from regular ibgp config (eg VRF, VPLS, etc)
            data = self.ebgp_session_data(session, ip_version = 4)
            ebgp_neighbors.append(data)

        g_ebgp_v6 = self.anm['ebgp_v6']
        for session in sort_sessions(g_ebgp_v6.edges(phy_node)):
            if session.exclude:
                log.debug("Skipping excluded ebgp session %s" % session)
                continue # exclude from regular ibgp config (eg VRF, VPLS, etc)
            data = self.ebgp_session_data(session, ip_version = 6)
            ebgp_neighbors.append(data)

        node.bgp.ebgp_neighbors = ebgp_neighbors
        node.bgp.ebgp_neighbors.sort("asn")

        return

    def eigrp(self, node):
        g_eigrp = self.anm['eigrp']
        g_ipv4 = self.anm['ipv4']
        eigrp_node = self.anm['eigrp'].node(node)
        node.eigrp.name = eigrp_node.name

        ipv4_networks = set()
        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface
            ipv4_int = g_ipv4.interface(interface)
            eigrp_int = g_eigrp.interface(interface)
            if not eigrp_int.is_bound:
                continue # not an EIGRP interface
            network = ipv4_int.subnet
            if eigrp_int and eigrp_int.is_bound:
                ipv4_networks.add(network)

        # Loopback zero subnet
        ipv4_networks.add(node.loopback_zero.ipv4_cidr)

        node.eigrp.ipv4_networks = sorted(list(ipv4_networks))

    def isis(self, node):
        g_isis = self.anm['isis']

        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface

            phy_int = self.anm['phy'].interface(interface)

            isis_int = phy_int['isis']
            if isis_int and isis_int.is_bound:
                isis_node = g_isis.node(node)
                interface.isis = {
                        'metric': isis_int.metric,
                        'process_id': node.isis.process_id,
                        'use_ipv4': node.ip.use_ipv4,
                        'use_ipv6': node.ip.use_ipv6,
                        'multipoint': isis_int.multipoint,
                        } #TODO: add wrapper for this

        g_isis = self.anm['isis']
        isis_node = self.anm['isis'].node(node)
        node.isis.net = isis_node.net
        node.isis.process_id = isis_node.process_id
        node.isis.lo_interface = self.lo_interface
# set isis on loopback_zero

        node.loopback_zero.isis = {
                        'use_ipv4': node.ip.use_ipv4,
                        'use_ipv6': node.ip.use_ipv6,
                        } #TODO: add wrapper for this

