from autonetkit.compilers.device.router_base import RouterCompiler
from autonetkit.ank import sn_preflen_to_network
from collections import defaultdict
import netaddr
from autonetkit.compiler import sort_sessions
import autonetkit.log as log

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

        if node in self.anm['ospf']:
            node.ospf.use_ipv4 = phy_node.use_ipv4
            node.ospf.use_ipv6 = phy_node.use_ipv6

        if node in self.anm['eigrp']:
            node.eigrp.use_ipv4 = phy_node.use_ipv4
            node.eigrp.use_ipv6 = phy_node.use_ipv6

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
            for session in sort_sessions(g_ibgp_v4.edges(vrf_node)):
                if session.exclude and session.vrf:
                    data = self.ibgp_session_data(session, ip_version = 4)
                    vrf_ibgp_neighbors[session.vrf].append(data)

            g_ibgp_v6 = self.anm['ibgp_v6']
            for session in sort_sessions(g_ibgp_v6.edges(vrf_node)):
                if session.exclude and session.vrf:
                    data = self.ibgp_session_data(session, ip_version = 6)
                    vrf_ibgp_neighbors[session.vrf].append(data)

            # eBGP sessions for this VRF
            vrf_ebgp_neighbors = defaultdict(list)

            g_ebgp_v4 = self.anm['ebgp_v4']
            for session in sort_sessions(g_ebgp_v4.edges(vrf_node)):
                if session.exclude and session.vrf:
                    data = self.ebgp_session_data(session, ip_version = 4)
                    vrf_ebgp_neighbors[session.vrf].append(data)

            g_ebgp_v6 = self.anm['ebgp_v6']
            for session in sort_sessions(g_ebgp_v6.edges(vrf_node)):
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


    def eigrp(self, node):
        super(IosBaseCompiler, self).eigrp(node)
        for interface in node.physical_interfaces:
            phy_int = self.anm['phy'].interface(interface)

            eigrp_int = phy_int['eigrp']
            if eigrp_int and eigrp_int.is_bound:
                if interface.exclude_igp:
                    continue # don't configure IGP for this interface

                interface.eigrp = {
                        'metric': eigrp_int.metric,
                        'area': eigrp_int.area,
                        'name': node.eigrp.name,
                        'use_ipv4': node.ip.use_ipv4,
                        'use_ipv6': node.ip.use_ipv6,
                        'multipoint': eigrp_int.multipoint,
                        } #TODO: add wrapper for this

    def isis(self, node):
        super(IosBaseCompiler, self).isis(node)
        for interface in node.physical_interfaces:
            isis_int = self.anm['isis'].interface(interface)
            edges = isis_int.edges()
            if len(edges) != 1:
                log.warning("Extended IOS config support not valid for multipoint ISIS connections")
                continue
                #TODO multipoint handling?
            edge = edges[0]
            dst = edge.dst
            if not dst.is_router:
                log.debug("Connection to non-router host not added to IGP")
                continue

            src_type = node.device_subtype
            dst_type = dst['phy'].device_subtype
            if src_type == "xrvr":
                if dst_type == "vios":
                    interface.isis.hello_padding_disable = True
                elif dst_type == "CSR1000v":
                    interface.isis.hello_padding_disable = True
                elif dst_type == "titanium":
                    interface.isis.hello_padding_disable = True

            if src_type == "vios":
                if dst_type == "xrvr":
                    interface.isis.mtu = 1430

            if src_type == "CSR1000v":
                if dst_type == "xrvr":
                    interface.isis.mtu = 1430

            if src_type == "titanium":
                if dst_type == "xrvr":
                    interface.mtu = 1430 # for all of interface
                    interface.isis.hello_padding_disable = True
                elif dst_type == "vios":
                    interface.isis.hello_padding_disable = True
                elif dst_type == "CSR1000v":
                    interface.isis.hello_padding_disable = True

            interface.isis_mtu = interface.isis.mtu
            interface.hello_padding_disable = interface.isis.hello_padding_disable

class IosClassicCompiler(IosBaseCompiler):

    def compile(self, node):
        super(IosClassicCompiler, self).compile(node)
        phy_node = self.anm['phy'].node(node)
        if phy_node.device_subtype == "vios":
            # only copy across for certain reference platforms
            node.use_onepk = phy_node.use_onepk
            node.no_service_config = True

        if phy_node.device_subtype == "CSR1000v":
            # only copy across for certain reference platforms
            node.transport_input_ssh_telnet = True
            node.include_csr = True
            # Set secret password to "cisco"
            node.enable_secret = "tnhtc92DXBhelxjYk8LWJrPV36S2i4ntXrpb4RFmfqY"

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

        #vpnv4_neighbors = natural_sort(vpnv4_neighbors, key = lambda x: x['dst_int_ip'])
        vpnv4_neighbors = sorted(vpnv4_neighbors, key = lambda x: x['loopback'])
        node.bgp.vpnv4_neighbors = vpnv4_neighbors

class IosXrCompiler(IosBaseCompiler):
    def ospf(self, node):
        super(IosXrCompiler, self).ospf(node)
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

    def eigrp(self, node):
        super(IosXrCompiler, self).eigrp(node)

        node.eigrp.name = 1 #TODO: check if this should be ASN

        g_eigrp = self.anm['eigrp']
        ipv4_interfaces = []
        ipv6_interfaces = []

        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface

            eigrp_int = g_eigrp.interface(interface)
            if eigrp_int and eigrp_int.is_bound:
                data = {'id': interface.id, 'passive': False}
                if node.eigrp.use_ipv4:
                    ipv4_interfaces.append(data)
                if node.eigrp.use_ipv6:
                    ipv6_interfaces.append(data)

        loopback_zero = node.loopback_zero
        data = {'id': node.loopback_zero.id, 'passive': True}
        if node.eigrp.use_ipv4:
            ipv4_interfaces.append(data)
        if node.eigrp.use_ipv6:
            ipv6_interfaces.append(data)

        node.eigrp.ipv4_interfaces = ipv4_interfaces
        node.eigrp.ipv6_interfaces = ipv6_interfaces

    def isis(self, node):
        super(IosXrCompiler, self).isis(node)
        node.isis.isis_links = []

        for interface in node.physical_interfaces:
            if interface.exclude_igp:
                continue # don't configure IGP for this interface

            #print interface.isis.dump()
            # copy across attributes from the IosBaseCompiler setting step

            isis_int = self.anm['isis'].interface(interface)
            if isis_int and isis_int.is_bound:
                data = {
                        'id': interface.id,
                        'metric': isis_int.metric,
                        'multipoint': isis_int.multipoint,
                        }
                if interface.isis.hello_padding_disable is not None:
                    data['hello_padding_disable'] = interface.isis.hello_padding_disable
                if interface.isis.mtu is not None:
                    data['mtu'] = interface.isis.hello_padding_disable

                node.isis.isis_links.append(**data)

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

    def eigrp(self, node):
        ##TODO: do we want to specify the name or hard-code (as currently)?
        super(NxOsCompiler, self).eigrp(node)
        loopback_zero = node.loopback_zero
        loopback_zero.eigrp = {
                'use_ipv4': node.ip.use_ipv4,
                'use_ipv6': node.ip.use_ipv6,
                }


class StarOsCompiler(IosBaseCompiler):
    pass
