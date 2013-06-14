import autonetkit.ank as ank
import itertools
import netaddr
import os
from collections import defaultdict
import string
from datetime import datetime
import autonetkit.log as log
import autonetkit.plugins.naming as naming
import autonetkit.config
from autonetkit.ank_utils import alphabetical_sort as alpha_sort
from autonetkit.ank import sn_preflen_to_network

def dot_to_underscore(instring):
    """Replace dots with underscores"""
    return instring.replace(".", "_")

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

    """Base Router compiler"""
    def __init__(self, nidb, anm):
        self.nidb = nidb
        self.anm = anm

    def compile(self, node):
        phy_node = self.anm['phy'].node(node)
        ipv4_node = self.anm['ipv4'].node(node)

        node.ip.use_ipv4 = phy_node.use_ipv4 or False
        node.ip.use_ipv6 = phy_node.use_ipv6 or False
        if not (node.ip.use_ipv4 and node.ip.use_ipv6):
            log.debug("Neither IPv4 nor IPv6 specified for %s, using IPv4" % node)
            node.ip.use_ipv4 = True

        node.label = naming.network_hostname(phy_node)
        node.input_label = phy_node.id
        node.loopback = ipv4_node.loopback
        node.loopback_subnet = netaddr.IPNetwork(node.loopback)
        node.loopback_subnet.prefixlen = 32

        self.interfaces(node)
        if node in self.anm['ospf']:
            self.ospf(node)
        if node in self.anm['isis']:
            self.isis(node)
        if node in self.anm['bgp']:
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
            if node.ip.use_ipv4:
                ipv4_int = phy_int['ipv4']
                interface.use_ipv4 = True
                interface.ipv4_address = ipv4_int.ip_address
                interface.ipv4_subnet = ipv4_int.subnet
                interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                        interface.ipv4_subnet.prefixlen)

            if node.ip.use_ipv6:
                ipv6_int = phy_int['ipv6']
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
                #print "here for non zero", interface.id
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
                pass

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
        for session in g_ibgp_v4.edges(phy_node):
            if session.exclude:
                log.debug("Skipping excluded ibgp session %s" % session)
                continue # exclude from regular ibgp config (eg for VRF, VPLS, etc)

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
        for session in g_ibgp_v6.edges(phy_node):
            if session.exclude:
                log.debug("Skipping excluded ibgp session %s" % session)
                continue # exclude from regular ibgp config (eg for VRF, VPLS, etc)
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
        for session in g_ebgp_v4.edges(phy_node):
            if session.exclude:
                log.debug("Skipping excluded ebgp session %s" % session)
                continue # exclude from regular ibgp config (eg for VRF, VPLS, etc)
            data = self.ebgp_session_data(session, ip_version = 4)
            ebgp_neighbors.append(data)

        g_ebgp_v6 = self.anm['ebgp_v6']
        for session in g_ebgp_v6.edges(phy_node):
            if session.exclude:
                log.debug("Skipping excluded ebgp session %s" % session)
                continue # exclude from regular ibgp config (eg for VRF, VPLS, etc)
            data = self.ebgp_session_data(session, ip_version = 6)
            ebgp_neighbors.append(data)

        node.bgp.ebgp_neighbors = ebgp_neighbors
        node.bgp.ebgp_neighbors.sort("asn")

        return

    def isis(self, node):
        g_isis = self.anm['isis']
        node.isis.isis_links = []

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

                node.isis.isis_links.append(
                        id = interface.id,
                        metric = isis_int.metric,
                        multipoint= isis_int.multipoint,
                        )

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
            node.loopback_zero.ipv4_address=ipv4_node.loopback
            node.loopback_zero.ipv4_subnet=node.loopback_subnet

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

# TODO: Don't render netkit lab topology if no netkit hosts

class IosBaseCompiler(RouterCompiler):
    """Base IOS compiler"""

    lo_interface_prefix = "Loopback"
    lo_interface = "%s%s" % (lo_interface_prefix, 0)

    def ibgp_session_data(self, session, ip_version):
        """Wraps RouterCompiler ibgp_session_data
        adds vpnv4 = True if ip_version == 4 and session is in g_ibgp_vpn_v4"""
        data = super(IosBaseCompiler, self).ibgp_session_data(session, ip_version)
        if ip_version == 4:
            g_ibgp_vpn_v4 = self.anm['ibgp_vpn_v4']
            if g_ibgp_vpn_v4.has_edge(session):
                data['use_vpnv4'] = True
        return data

    def compile(self, node):
        self.vrf_igp_interfaces(node)
        phy_node = self.anm['phy'].node(node)

        node.use_cdp = phy_node.use_cdp
        if phy_node.device_subtype == "os":
            # only copy across for certain reference platforms
            node.use_onepk = phy_node.use_onepk

        if node in self.anm['ospf']:
            node.ospf.use_ipv4 = phy_node.use_ipv4
            node.ospf.use_ipv6 = phy_node.use_ipv6

        if node in self.anm['isis']:
            node.isis.use_ipv4 = phy_node.use_ipv4
            node.isis.use_ipv6 = phy_node.use_ipv6

        super(IosBaseCompiler, self).compile(node)
        if node in self.anm['isis']:
            self.isis(node)

        node.label = self.anm['phy'].node(node).label
        """Note:
        VRFs are either: before, and mark IGP interfaces to skip;
        or after, and remove IGP interfaces
        """
        self.vrf(node)

    def interfaces(self, node):
        phy_loopback_zero = self.anm['phy'].interface(node.loopback_zero)
        if node.ip.use_ipv4:
            ipv4_loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")
            ipv4_loopback_zero = phy_loopback_zero['ipv4']
            ipv4_address = ipv4_loopback_zero.ip_address
            node.loopback_zero.use_ipv4 = True
            node.loopback_zero.ipv4_address = ipv4_address
            node.loopback_zero.ipv4_subnet = ipv4_loopback_subnet
            node.loopback_zero.ipv4_cidr = sn_preflen_to_network(
                    ipv4_address, ipv4_loopback_subnet.prefixlen)

        if node.ip.use_ipv6:
            node.loopback_zero.use_ipv6 = True
            ipv6_loopback_zero = phy_loopback_zero['ipv6']
            node.loopback_zero.ipv6_address = sn_preflen_to_network(
                ipv6_loopback_zero.ip_address, 128)

        super(IosBaseCompiler, self).interfaces(node)

        for interface in node.physical_interfaces:
            interface.use_cdp = node.use_cdp # use node value

    def bgp(self, node):
        node.bgp.lo_interface = self.lo_interface
        super(IosBaseCompiler, self).bgp(node)

        # Only advertise loopbacks into eBGP
        if node.ip.use_ipv4:
            node.bgp.ipv4_advertise_subnets = [node.loopback_zero.ipv4_cidr]
        if node.ip.use_ipv6:
            node.bgp.ipv6_advertise_subnets = [node.loopback_zero.ipv6_address]

        # vrf
        #TODO: this should be inside vrf section?
        node.bgp.vrfs = []

        vrf_node = self.anm['vrf'].node(node)
        if vrf_node and vrf_node.vrf_role is "PE":

            # iBGP sessions for this VRF
            vrf_ibgp_neighbors = defaultdict(list)

            g_ibgp_v4 = self.anm['ibgp_v4']
            for session in g_ibgp_v4.edges(vrf_node):
                if session.exclude and session.vrf:
                    data = self.ibgp_session_data(session, ip_version = 4)
                    vrf_ibgp_neighbors[session.vrf].append(data)

            g_ibgp_v6 = self.anm['ibgp_v6']
            for session in g_ibgp_v6.edges(vrf_node):
                if session.exclude and session.vrf:
                    data = self.ibgp_session_data(session, ip_version = 6)
                    vrf_ibgp_neighbors[session.vrf].append(data)

            # eBGP sessions for this VRF
            vrf_ebgp_neighbors = defaultdict(list)

            g_ebgp_v4 = self.anm['ebgp_v4']
            for session in g_ebgp_v4.edges(vrf_node):
                if session.exclude and session.vrf:
                    data = self.ebgp_session_data(session, ip_version = 4)
                    vrf_ebgp_neighbors[session.vrf].append(data)

            g_ebgp_v6 = self.anm['ebgp_v6']
            for session in g_ebgp_v6.edges(vrf_node):
                if session.exclude and session.vrf:
                    data = self.ebgp_session_data(session, ip_version = 6)
                    vrf_ebgp_neighbors[session.vrf].append(data)

            for vrf in vrf_node.node_vrf_names:
                rd_index = vrf_node.rd_indices[vrf]
                rd = "%s:%s" % (node.asn, rd_index)
                node.bgp.vrfs.append(
                    vrf=vrf,
                    rd=rd,
                    use_ipv4=node.ip.use_ipv4,
                    use_ipv6=node.ip.use_ipv6,
                    vrf_ebgp_neighbors = vrf_ebgp_neighbors[vrf],
                    vrf_ibgp_neighbors = vrf_ibgp_neighbors[vrf],
                )

        # Retain route_target if in ibgp_vpn_v4 and RR or HRR (set in design)
        vpnv4_node = self.anm['ibgp_vpn_v4'].node(node)
        if vpnv4_node:
            retain = False
            if vpnv4_node.retain_route_target:
                retain = True
            node.bgp.vpnv4 = {'retain_route_target': retain}

    def vrf_igp_interfaces(self, node):
        # marks physical interfaces to exclude from IGP
        vrf_node = self.anm['vrf'].node(node)
        if vrf_node and vrf_node.vrf_role is "PE":
            for interface in node.physical_interfaces:
                vrf_int = self.anm['vrf'].interface(interface)
                if vrf_int.vrf_name:
                    interface.exclude_igp = True

    def vrf(self, node):
        g_vrf = self.anm['vrf']
        vrf_node = self.anm['vrf'].node(node)
        node.vrf.vrfs = []
        if vrf_node and vrf_node.vrf_role is "PE":
            #TODO: check if mpls ldp already set elsewhere
            for vrf in vrf_node.node_vrf_names:
                route_target = g_vrf.data.route_targets[node.asn][vrf]
                rd_index = vrf_node.rd_indices[vrf]
                rd = "%s:%s" % (node.asn, rd_index)

                node.vrf.vrfs.append({
                    'vrf': vrf,
                    "rd": rd,
                    'route_target': route_target,
                })

            for interface in node.interfaces:
                vrf_int = self.anm['vrf'].interface(interface)
                if vrf_int.vrf_name:
                    interface.vrf = vrf_int.vrf_name # mark interface as being part of vrf
                    if interface.physical:
                        interface.description += " vrf %s" % vrf_int.vrf_name

        if vrf_node and vrf_node.vrf_role in ("P", "PE"):
            # Add PE -> P, PE -> PE interfaces to MPLS LDP
            node.mpls.ldp_interfaces = []
            for interface in node.physical_interfaces:
                mpls_ldp_int = self.anm['mpls_ldp'].interface(interface)
                if mpls_ldp_int.is_bound:
                    node.mpls.ldp_interfaces.append(interface.id)
                    interface.use_mpls = True

        if vrf_node and vrf_node.vrf_role is "P":
            node.mpls.ldp_interfaces = []
            for interface in node.physical_interfaces:
                node.mpls.ldp_interfaces.append(interface.id)

        vrf_node = self.anm['vrf'].node(node)

        node.vrf.use_ipv4 = node.ip.use_ipv4
        node.vrf.use_ipv6 = node.ip.use_ipv6
        node.vrf.vrfs.sort("vrf")

        if self.anm.has_overlay("mpls_ldp") and node in self.anm['mpls_ldp']:
            node.mpls.enabled = True
            node.mpls.router_id = node.loopback_zero.id

    def ospf(self, node):
        super(IosBaseCompiler, self).ospf(node)
        for interface in node.physical_interfaces:
            phy_int = self.anm['phy'].interface(interface)

            ospf_int = phy_int['ospf']
            if ospf_int and ospf_int.is_bound:
                if interface.exclude_igp:
                    continue # don't configure IGP for this interface

                interface.ospf = {
                        'cost': ospf_int.cost,
                        'area': ospf_int.area,
                        'process_id': node.ospf.process_id,
                        'use_ipv4': node.ip.use_ipv4,
                        'use_ipv6': node.ip.use_ipv6,
                        'multipoint': ospf_int.multipoint,
                        } #TODO: add wrapper for this

class IosClassicCompiler(IosBaseCompiler):

    def ospf(self, node):
        super(IosClassicCompiler, self).ospf(node)
        loopback_zero = node.loopback_zero
        ospf_node = self.anm['ospf'].node(node)
        loopback_zero.ospf = {
                        'cost': 1,
                        'area': ospf_node.area,
                        'process_id': node.ospf.process_id,
                        'use_ipv4': False,
                        'use_ipv6': node.ip.use_ipv6,
                        'multipoint': False,
                        } #TODO: add wrapper for this        


    def compile(self, node):
        super(IosClassicCompiler, self).compile(node)

        phy_node = self.anm['phy'].node(node)
        if phy_node.include_csr:
            node.include_csr = True

        node.platform_subtype = phy_node.device_subtype

    def bgp(self, node):
        super(IosClassicCompiler, self).bgp(node)

        vpnv4_neighbors = []
        if node.bgp.vpnv4:
            for neigh in node.bgp.ibgp_neighbors:
                if not neigh.use_ipv4:
                    continue
                #TODO: fix up limitation where can't add as overlay_data
                # (this causes problems serializing, when adding convert to dict?)
                neigh_data = dict(neigh)
                vpnv4_neighbors.append(neigh_data)

            for neigh in node.bgp.ibgp_rr_clients:
                if not neigh.use_ipv4:
                    continue
                neigh_data = dict(neigh)
                neigh_data['rr_client'] = True
                vpnv4_neighbors.append(neigh_data)

            for neigh in node.bgp.ibgp_rr_parents:
                if not neigh.use_ipv4:
                    continue
                neigh_data = dict(neigh)
                vpnv4_neighbors.append(neigh_data)

        node.bgp.vpnv4_neighbors = vpnv4_neighbors

class Ios2Compiler(IosBaseCompiler):

    def ospf(self, node):
        super(Ios2Compiler, self).ospf(node)
        g_ospf = self.anm['ospf']
        interfaces_by_area = defaultdict(list)

        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface

            ospf_int = g_ospf.interface(interface)
            if ospf_int and ospf_int.is_bound:
                area = ospf_int.area
                area = str(area) # can't serialize IPAddress object to JSON
                interfaces_by_area[area].append({
                    'id': interface.id,
                    'cost': int(ospf_int.cost),
                    'passive': False,
                })

        loopback_zero = node.loopback_zero
        ospf_loopback_zero = g_ospf.interface(loopback_zero)
        router_area = ospf_loopback_zero.area # area assigned to router
        router_area = str(router_area) # can't serialize IPAddress object to JSON
        interfaces_by_area[router_area].append({
            'id': node.loopback_zero.id,
            'cost': 0,
            'passive': True,
        })

        node.ospf.interfaces = dict( interfaces_by_area)

class NxOsCompiler(IosBaseCompiler):
    def interfaces(self, node):
# need to aggregate areas
        super(NxOsCompiler, self).interfaces(node)

    def ospf(self, node):
        super(NxOsCompiler, self).ospf(node)
        loopback_zero = node.loopback_zero
        g_ospf = self.anm['ospf']
        ospf_node = g_ospf.node(node)
        loopback_zero.ospf = {
                'cost': ospf_node.cost,
                'area': ospf_node.area,
                'process_id': node.ospf.process_id,
                'use_ipv4': node.ip.use_ipv4,
                'use_ipv6': node.ip.use_ipv6,
                } #TODO: add wrapper for this

        # TODO: configure OSPF on loopback like example

# Platform compilers

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

class JunosphereCompiler(PlatformCompiler):
    """Junosphere Platform Compiler"""
    def interface_ids(self):
        invalid = set([2])
        valid_ids = (x for x in itertools.count(0) if x not in invalid)
        for x in valid_ids:
            yield "ge-0/0/%s" % x

    def compile(self):
        log.info("Compiling Junosphere for %s" % self.host)
        g_phy = self.anm['phy']
        junos_compiler = JunosCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='junos'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","junos.mako")
            nidb_node.render.dst_folder = os.path.join("rendered",self.host,"junosphere")
            nidb_node.render.dst_file = "%s.conf" % ank.name_folder_safe(
                phy_node.label)

            int_ids = self.interface_ids()
            for interface in nidb_node.physical_interfaces:
                interface.unit = 0
                interface.id = int_ids.next()

            junos_compiler.compile(nidb_node)

class NetkitCompiler(PlatformCompiler):
    """Netkit Platform Compiler"""
    @staticmethod
    def index_to_int_id(index):
        return "eth%s" % index

    def compile(self):
        log.info("Compiling Netkit for %s" % self.host)
        g_phy = self.anm['phy']
        quagga_compiler = QuaggaCompiler(self.nidb, self.anm)
# TODO: this should be all l3 devices not just routers
        for phy_node in g_phy.nodes('is_l3device', host=self.host, syntax='quagga'):
            folder_name = naming.network_hostname(phy_node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.base = os.path.join("templates","quagga")
            nidb_node.render.template = os.path.join("templates","netkit_startup.mako")
            nidb_node.render.dst_folder = os.path.join("rendered", self.host, "netkit")
            nidb_node.render.base_dst_folder = os.path.join("rendered", self.host, "netkit", folder_name)
            nidb_node.render.dst_file = "%s.startup" % folder_name

# allocate zebra information
            if nidb_node.is_router:
                nidb_node.zebra.password = "1234"
            hostname = folder_name
            if hostname[0] in string.digits:
                hostname = "r" + hostname
            nidb_node.hostname = hostname  # can't have . in quagga hostnames
            nidb_node.ssh.use_key = True  # TODO: make this set based on presence of key

            # Note this could take external data
            int_ids = itertools.count(0)
            for interface in nidb_node.physical_interfaces:
                numeric_id = int_ids.next()
                interface.numeric_id = numeric_id
                interface.id = self.index_to_int_id(numeric_id)

# and allocate tap interface
            nidb_node.tap.id = self.index_to_int_id(int_ids.next())

            quagga_compiler.compile(nidb_node)

            # TODO: move these into inherited BGP config
            if nidb_node.bgp:
                nidb_node.bgp.debug = True
                static_routes = []
                nidb_node.zebra.static_routes = static_routes

        # and lab.conf
        self.allocate_tap_ips()
        self.lab_topology()

    def allocate_tap_ips(self):
        settings = autonetkit.config.settings
        # TODO: take tap subnet parameter
        #TODO: this should be tuple of self.host and platform
        lab_topology = self.nidb.topology[self.host]
            # TODO: also store platform
        from netaddr import IPNetwork
        address_block = IPNetwork(settings.get("tapsn")
            or "172.16.0.0/16").iter_hosts() # added for backwards compatibility
        lab_topology.tap_host = address_block.next()
        lab_topology.tap_vm = address_block.next()  # for tunnel host
        for node in sorted(self.nidb.nodes("is_l3device", host=self.host)):
            # TODO: fix sorting order
            # TODO: check this works for switches
            node.tap.ip = address_block.next()

    def lab_topology(self):
# TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology[self.host]
        lab_topology.render_template = os.path.join("templates","netkit_lab_conf.mako")
        lab_topology.render_dst_folder = os.path.join("rendered", self.host, "netkit")
        lab_topology.render_dst_file = "lab.conf"
        lab_topology.description = "AutoNetkit Lab"
        lab_topology.author = "AutoNetkit"
        lab_topology.web = "www.autonetkit.org"
        host_nodes = list(
            self.nidb.nodes(host=self.host, platform="netkit"))
        if not len(host_nodes):
            log.debug("No Netkit hosts for %s" % self.host)
            # TODO: make so can return here
            # return
# also need collision domains for this host
        cd_nodes = self.nidb.nodes("collision_domain", host=self.host)
        host_nodes += cd_nodes
        subgraph = self.nidb.subgraph(host_nodes, self.host)

# TODO: sort this numerically, not just by string
        lab_topology.machines = " ".join(alpha_sort(naming.network_hostname(phy_node)
            for phy_node in subgraph.nodes("is_l3device")))

        lab_topology.config_items = []
        for node in sorted(subgraph.nodes("is_l3device")):
            for interface in node.physical_interfaces:
                collision_domain = str(interface.ipv4_subnet).replace("/", ".")
                numeric_id = interface.numeric_id #netkit lab.conf uses 1 instead of eth1
                lab_topology.config_items.append(
                    device=naming.network_hostname(node),
                    key=numeric_id,
                    value=collision_domain,
                )

        lab_topology.tap_ips = []
        for node in subgraph:
            if node.tap:
                lab_topology.tap_ips.append(
                    # TODO: merge the following and previous into a single
                    # function
                    device=naming.network_hostname(node),
                    id=node.tap.id.replace("eth", ""),  # strip ethx -> x
                    ip=node.tap.ip,
                )

        lab_topology.tap_ips.sort("ip")
        lab_topology.config_items.sort("device")

class CiscoCompiler(PlatformCompiler):
    """Platform compiler for Cisco"""

    # def __init__(self, nidb, anm, host):
# TODO: setup to remap allocate interface id function here
        # super(CiscoCompiler, self).__init__(nidb, anm, host)


    @staticmethod
    def numeric_to_interface_label_ios(x):
        """Starts at GigabitEthernet0/1 """
        x = x + 1 
        return "GigabitEthernet0/%s" % x

    @staticmethod
    def numeric_to_interface_label_ra(x):
        """Starts at Gi0/1
        #TODO: check"""
        x = x + 1
        return "GigabitEthernet%s" % x

    @staticmethod
    def numeric_to_interface_label_nxos(x):
        return "Ethernet2/%s" % x

    @staticmethod
    def numeric_to_interface_label_ios2(x):
        return "GigabitEthernet0/0/0/%s" % x

    @staticmethod
    def loopback_interface_ids():
        for x in itertools.count(100): # start at 100 for secondary
            prefix = IosBaseCompiler.lo_interface_prefix
            yield "%s%s" % (prefix, x)

    @staticmethod
    def interface_ids_ios():
        #TODO: make this skip if in list of allocated ie [interface.name for interface in node]
        for x in itertools.count(0):
            yield "GigabitEthernet0/%s" % x

    @staticmethod
    def interface_ids_ra():
        #TODO: make this skip if in list of allocated ie [interface.name for interface in node]
        for x in itertools.count(0):
            yield "GigabitEthernet%s" % x

    @staticmethod
    def interface_ids_nxos():
        for x in itertools.count(0):
            yield "Ethernet2/%s" % x

    @staticmethod
    def interface_ids_ios2():
        for x in itertools.count(0):
            yield "GigabitEthernet0/0/0/%s" % x

    @staticmethod
    def numeric_interface_ids():
        """#TODO: later skip interfaces already taken"""
        for x in itertools.count(0):
            yield x

    def compile(self):
        settings = autonetkit.config.settings
        to_memory = settings['Compiler']['Cisco']['to memory']
#TODO: need to copy across the interface name from edge to the interface
        g_phy = self.anm['phy']
        use_mgmt_interfaces = g_phy.data.mgmt_interfaces_enabled 
        if use_mgmt_interfaces:
            log.info("Allocating management interfaces for Cisco")
        else:
            log.info("Not allocating management interfaces for Cisco")

        log.info("Compiling Cisco for %s" % self.host)
        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        now = datetime.now()
        if settings['Compiler']['Cisco']['timestamp']:
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            dst_folder = os.path.join("rendered", self.host, timestamp, "cisco")
        else:
            dst_folder = os.path.join("rendered", self.host, "cisco")
# TODO: merge common router code, so end up with three loops: routers, ios
# routers, ios2 routers

        # store autonetkit_cisco version
        from pkg_resources import get_distribution
        ank_cisco_version = get_distribution("autonetkit_cisco").version

        for phy_node in g_phy.nodes('is_router', host=self.host):
            loopback_ids = self.loopback_interface_ids()
            # allocate loopbacks to routes (same for all ios variants)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.ank_cisco_version = ank_cisco_version

            for interface in nidb_node.loopback_interfaces:
                if interface != nidb_node.loopback_zero:
                    interface.id = loopback_ids.next()

            # numeric ids
            numeric_int_ids = self.numeric_interface_ids()
            for interface in nidb_node.physical_interfaces:
                phy_numeric_id = phy_node.interface(interface).numeric_int_id
                if phy_numeric_id is None:
                    interface.numeric_id = numeric_int_ids.next() 
                else:
                    interface.numeric_id = int(phy_numeric_id) 

        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios'):
            specified_int_names = phy_node.specified_int_names
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","ios.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            #TODO: write function that assigns interface number excluding those already taken

            # Assign interfaces
            if phy_node.device_subtype == "os":
                int_ids = self.interface_ids_ios()
                numeric_to_interface_label = self.numeric_to_interface_label_ios
            elif phy_node.device_subtype == "ra":
                int_ids = self.interface_ids_ra()
                numeric_to_interface_label = self.numeric_to_interface_label_ra
            else:
                # default if no subtype specified
                #TODO: need to set default in the load module
                log.warning("Unexpected subtype %s" % phy_node.device_subtype)
                int_ids = self.interface_ids_ios()
                numeric_to_interface_label = self.numeric_to_interface_label_ios
                
            if use_mgmt_interfaces:
                mgmt_int_id = int_ids.next()  # 0/0 is used for management ethernet

            for interface in nidb_node.physical_interfaces:
                # map numeric id to label
                interface.label = numeric_to_interface_label(interface.numeric_id)

                if specified_int_names:
                    interface.id = phy_node.interface(interface).name
                # TODO: need to determine if interface name already specified
                else:
                    interface.id = int_ids.next()

            ios_compiler.compile(nidb_node)
            if use_mgmt_interfaces:
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

        ios2_compiler = Ios2Compiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios2'):
            specified_int_names = phy_node.specified_int_names
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","ios2","router.conf.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios2()
            for interface in nidb_node.physical_interfaces:
                interface.label = self.numeric_to_interface_label_ios2(interface.numeric_id)
                if specified_int_names:
                    interface.id = phy_node.interface(interface).name
                # TODO: need to determine if interface name already specified
                else:
                    interface.id = int_ids.next()

            ios2_compiler.compile(nidb_node)

            if use_mgmt_interfaces:
                mgmt_int_id = "mgmteth0/0/CPU0/0"
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

        nxos_compiler = NxOsCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='nx_os'):
            specified_int_names = phy_node.specified_int_names
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","nx_os.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_nxos()
            for interface in nidb_node.physical_interfaces:
                interface.label = self.numeric_to_interface_label_nxos(interface.numeric_id)
                if specified_int_names:
                    interface.id = phy_node.interface(interface).name
                # TODO: need to determine if interface name already specified
                else:
                    interface.id = int_ids.next()

            if use_mgmt_interfaces:
                mgmt_int_id = "mgmt0"
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

            nxos_compiler.compile(nidb_node)

        other_nodes = [phy_node for phy_node in g_phy.nodes('is_router', host=self.host)
                       if phy_node.syntax not in ("ios", "ios2")]
        for node in other_nodes:
            #TODO: check why we need this
            phy_node = g_phy.node(node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.input_label = phy_node.id  # set specifically for now for other variants

# TODO: use more os.path.join for render folders
# TODO: Split compilers into seperate modules

        if use_mgmt_interfaces:
            self.assign_management_interfaces()

    def assign_management_interfaces(self):
        g_phy = self.anm['phy']
        lab_topology = self.nidb.topology[self.host]
        oob_management_ips = {}

        #TODO: make this seperate function
        from netaddr import IPNetwork, IPRange

        mgmt_address_start = g_phy.data.mgmt_address_start 
        mgmt_address_end = g_phy.data.mgmt_address_end 
        mgmt_prefixlen = int(g_phy.data.mgmt_prefixlen)

        #TODO: need to check if range is insufficient
        mgmt_ips = (IPRange(mgmt_address_start, mgmt_address_end))
        mgmt_ips_iter = iter(mgmt_ips) # to iterate over

        mgmt_address_start_network = IPNetwork(mgmt_address_start) # as /32 for supernet
        mgmt_address_end_network = IPNetwork(mgmt_address_end) # as /32 for supernet
        # retrieve the first supernet, as this is the range requested. subsequent are the subnets
        start_subnet = mgmt_address_start_network.supernet(mgmt_prefixlen)[0] # retrieve first
        end_subnet = mgmt_address_end_network.supernet(mgmt_prefixlen)[0] # retrieve first

        try: # validation
            assert(start_subnet == end_subnet)
            log.debug("Verified: Cisco management subnets match")
        except AssertionError:
            log.warning("Error: Cisco management subnets do not match: %s and %s, using start subnet"
                    % (start_subnet, end_subnet))

        mgmt_subnet = start_subnet
        hosts_to_allocate = sorted(self.nidb.nodes('is_router', host=self.host))
        dhcp_subtypes = {"os"}
        dhcp_hosts = [h for h in hosts_to_allocate if h.device_subtype in dhcp_subtypes]
        non_dhcp_hosts = [h for h in hosts_to_allocate if h.device_subtype not in dhcp_subtypes]

        try: # validation
            assert(len(mgmt_ips) >= len(non_dhcp_hosts))
            log.debug("Verified: Cisco management IP range is sufficient size %s for %s hosts"
                    % (len(mgmt_ips), len(non_dhcp_hosts)))
        except AssertionError:
            log.warning("Error: Cisco management IP range is insufficient size %s for %s hosts"
                    % (len(mgmt_ips), len(non_dhcp_hosts)))
            # TODO: need to use default range
            return

        for nidb_node in hosts_to_allocate:
            for interface in nidb_node.physical_interfaces:
                if interface.management:
                    interface.description = "OOB Management"
                    interface.physical = True
                    interface.mgmt = True
                    if nidb_node.ip.use_ipv4:
                        interface.use_ipv4 = True
                    if nidb_node in dhcp_hosts:
                        interface.use_dhcp = True
                        oob_management_ips[str(nidb_node)] = "dhcp"
                    else:
                        ipv4_address = mgmt_ips_iter.next()
                        interface.ipv4_address = ipv4_address
                        interface.ipv4_subnet = mgmt_subnet
                        interface.ipv4_cidr = sn_preflen_to_network(ipv4_address, mgmt_prefixlen)
                        oob_management_ips[str(nidb_node)] = ipv4_address

        lab_topology.oob_management_ips = oob_management_ips

class DynagenCompiler(PlatformCompiler):
    """Dynagen Platform Compiler"""
    config_dir = "configs"

    @staticmethod
    def console_ports():
        """Interator for console ports"""
        for x in itertools.count(2001):
            yield x

    @staticmethod
    def interface_ids():
        """Allocate with slot and port iterating """
        id_pairs = ((slot + 1, port) for (
            slot, port) in itertools.product(xrange(4), xrange(2)))
        for (slot, port) in id_pairs:
            yield "f%s/%s" % (slot, port)

    def compile(self):
        log.info("Compiling Dynagen for %s" % self.host)
        g_phy = self.anm['phy']
        G_graphics = self.anm['graphics']
        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios'):
            nidb_node = self.nidb.node(phy_node)
            graphics_node = G_graphics.node(phy_node)
            nidb_node.render.template = os.path.join("templates", "ios.mako")
            nidb_node.render.dst_folder = os.path.join(
                "rendered", self.host, "dynagen", self.config_dir)
            nidb_node.render.dst_file = "%s.cfg" % ank.name_folder_safe(
                phy_node.label)

            # TODO: may want to normalise x/y
            nidb_node.x = graphics_node.x
            nidb_node.y = graphics_node.y

            # Allocate edges
            # assign interfaces
            # Note this could take external data
            int_ids = self.interface_ids()
            for interface in nidb_node.physical_interfaces:
                interface.id = int_ids.next()

            ios_compiler.compile(nidb_node)

        self.allocate_ports()
        self.lab_topology()

    def allocate_ports(self):
        # TODO: take tap subnet parameter
        con_ports = self.console_ports()

        for node in sorted(self.nidb.nodes("is_l3device", host=self.host)):
            # TODO: fix sorting order
            # TODO: check this works for switches
            node.console_port = con_ports.next()
            node.aux_port = node.console_port + 500

    def lab_topology(self):
# TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology[self.host]
        lab_topology.render_template = os.path.join("templates","dynagen.mako")
        lab_topology.render_dst_folder = os.path.join("rendered", self.host, "dynagen")
        lab_topology.render_dst_file = "topology.net"

        lab_topology.config_dir = self.config_dir

        # TODO: pick these up from config
        lab_topology.hypervisor_server = "127.0.0.1"
        lab_topology.hypervisor_port = "7200"
        lab_topology.image = "router.image"
        lab_topology.idlepc = "0x60629004"

        lab_topology.routers = []
        routers = list(
            self.nidb.routers(host=self.host, platform="dynagen"))

        for router in routers:
            phy_node = self.anm['phy'].node(router)
            interfaces = []

            for link in phy_node.edges():
                nidb_edge = self.nidb.edge(link)
                # need to find the reverse link, and its place in nidb for port
# TODO: tidy this up once have interfaces implemented
                back_link = self.anm['phy'].edges(link.dst, phy_node).next()
                back_link_nidb = self.nidb.edge(back_link)
                interfaces.append({
                    'src_port': nidb_edge.id,
                    'dst': str(link.dst),
                    'dst_port': back_link_nidb.id,
                })

            slots = []
            import math
            number_of_slots = int(math.ceil(1.0 * len(interfaces) / 2))
            slots = [(index + 1, "PA-2FE-TX") for index in range(
                number_of_slots)]
            cnfg = os.path.join(self.config_dir, router.render.dst_file)

            lab_topology.routers.append(
                hostname=str(router),
                model=7200,
                console=router.console_port,
                aux=router.aux_port,
                interfaces=interfaces,
                x=router.x,
                y=router.y,
                slots=slots,
                cnfg=cnfg,
            )

        lab_topology.routers.sort("hostname")
        return
