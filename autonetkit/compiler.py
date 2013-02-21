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
settings = autonetkit.config.settings
from autonetkit.ank_utils import alphabetical_sort as alpha_sort


def address_prefixlen_to_network(address, prefixlen):
    """Workaround for creating an IPNetwork from an address and a prefixlen
    TODO: check if this is part of netaddr module
    """
    return netaddr.IPNetwork("%s/%s" % (address, prefixlen))


def dot_to_underscore(instring):
    """Replace dots with underscores"""
    return instring.replace(".", "_")


class RouterCompiler(object):
    """Base router compiler"""
    lo_interface = "lo0"
    lo_interface_prefix = "lo"
# and set per platform

    """Base Router compiler"""
    def __init__(self, nidb, anm):
        self.nidb = nidb
        self.anm = anm

    def compile(self, node):
        phy_node = self.anm['phy'].node(node)
        ipv4_node = self.anm['ipv4'].node(node)

        node.ip.use_ipv4 = phy_node.use_ipv4
        node.ip.use_ipv6 = phy_node.use_ipv6

        node.label = naming.network_hostname(phy_node)
        node.input_label = phy_node.id
        node.loopback = ipv4_node.loopback
        node.loopback_subnet = netaddr.IPNetwork(node.loopback)
        node.loopback_subnet.prefixlen = 32

        self.interfaces(node)
        if node in self.anm['ospf']:
            self.ospf(node)
        if node in self.anm['bgp']:
            self.bgp(node)

    def interfaces(self, node):
        phy_node = self.anm['phy'].node(node)
        g_ipv4 = self.anm['ipv4']
        g_ipv6 = self.anm['ipv6']
        node.interfaces = []
        for link in phy_node.edges():
            nidb_edge = self.nidb.edge(link)

            ipv4_cidr = ipv6_address = ipv4_address = ipv4_subnet = None
            if node.ip.use_ipv4:
                ipv4_link = g_ipv4.edge(link)
                ipv4_address = ipv4_link.ip_address
                ipv4_subnet = ipv4_link.dst.subnet
                ipv4_cidr = address_prefixlen_to_network(ipv4_address,
                                                         ipv4_subnet.prefixlen)
            if node.ip.use_ipv6:
                ipv6_link = g_ipv6.edge(link)
                ipv6_subnet = ipv6_link.dst.subnet
                ipv6_address = address_prefixlen_to_network(ipv6_link.ip,
                                                            ipv6_subnet.prefixlen)

            node.interfaces.append(
                _edge_id=link.edge_id,  # used if need to append
                id=nidb_edge.id,
                description="%s to %s" % (link.src, link.dst),
                ipv4_address=ipv4_address,
                ipv4_subnet=ipv4_subnet,
                ipv4_cidr=ipv4_cidr,
                ipv6_address=ipv6_address,
                physical=True,
            )

        for index, interface in enumerate(phy_node.interfaces("is_loopback")):
            ip_interface = g_ipv4.node(node).interface(interface)
            vrf_interface = self.anm['vrf'].node(node).interface(interface)
            index = index + 1  # loopback0 (ie index 0) is reserved
            interface_id = "%s%s" % (self.lo_interface_prefix, index)
            node.interfaces.append(
                id=interface_id,
                description=interface.description,
                ipv4_address=ip_interface.loopback,
                ipv4_subnet=node.loopback_subnet,
                vrf_name=vrf_interface.vrf_name,
            )

        node.interfaces.sort("id")

    def ospf(self, node):
        """Returns OSPF links, also sets process_id
        """
        g_ospf = self.anm['ospf']
        g_ipv4 = self.anm['ipv4']

        node.ospf.loopback_area = g_ospf.node(node).area

        phy_node = self.anm['phy'].node(node)
        node.ospf.process_id = 1
        node.ospf.lo_interface = self.lo_interface
        node.ospf.ospf_links = []
        added_networks = set()
        for link in g_ospf.edges(phy_node):
            ip_link = g_ipv4.edge(link)
            if not ip_link:
                # TODO: fix this: due to multi edges from router to same switch
                # cluster
                continue
            network = ip_link.dst.subnet,
            if network not in added_networks:  # don't add more than once
                added_networks.add(network)
                node.ospf.ospf_links.append(
                    network=ip_link.dst.subnet,
                    area=link.area,
                )

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
            node.bgp.ipv6_advertise_subnets = g_ipv6.data.infra_blocks.get(
                asn) or []

        node.bgp.ibgp_neighbors = []
        node.bgp.ibgp_rr_clients = []
        node.bgp.ibgp_rr_parents = []
        node.bgp.ebgp_neighbors = []

        def format_session(session, use_ipv4=False, use_ipv6=False):
            neigh = session.dst
            if use_ipv4:
                neigh_ip = g_ipv4.node(neigh)
            elif use_ipv6:
                neigh_ip = g_ipv6.node(neigh)
            else:
                log.debug(
                    "Neither v4 nor v6 selected for BGP session %s, skipping"
                    % session)
                return

            if session.type == "ibgp":
                data = {
                    'neighbor': neigh.label,
                    'use_ipv4': use_ipv4,
                    'use_ipv6': use_ipv6,
                    'asn': neigh.asn,
                    'loopback': neigh_ip.loopback,
                    # TODO: this is platform dependent???
                    'update_source': "loopback 0",
                }
                if session.direction == 'down':
                    # ibgp_rr_clients[key] = data
                    node.bgp.ibgp_rr_clients.append(data)
                elif session.direction == 'up':
                    node.bgp.ibgp_rr_parents.append(data)
                else:
                    node.bgp.ibgp_neighbors.append(data)
            else:
                # TODO: fix this: this is a workaround for Quagga next-hop
                # denied for loopback (even with static route)
                ip_link = g_ipv4.edge(session)
                dst_int_ip = g_ipv4.edges(ip_link.dst, neigh).next(
                ).ip_address  # TODO: split this to a helper function

                # TODO: make this a returned value
                node.bgp.ebgp_neighbors.append({
                    'neighbor': neigh.label,
                    'use_ipv4': use_ipv4,
                    'use_ipv6': use_ipv6,
                    'asn': neigh.asn,
                    'loopback': neigh_ip.loopback,
                    'local_int_ip': ip_link.ip_address,
                    'dst_int_ip': dst_int_ip,
                    # TODO: change templates to access from node.bgp.lo_int
                    'update_source': self.lo_interface,
                })

        for session in g_bgp.edges(phy_node):
            if node.ip.use_ipv4:
                format_session(session, use_ipv4=True)
            if node.ip.use_ipv6:
                format_session(session, use_ipv6=True)
        node.bgp.ebgp_neighbors.sort("asn")

        return


class QuaggaCompiler(RouterCompiler):
    """Base Quagga compiler"""
    lo_interface = "lo0:1"

    def compile(self, node):
        super(QuaggaCompiler, self).compile(node)
        if node in self.anm['isis']:
            self.isis(node)

    def interfaces(self, node):
        """Quagga interface compiler"""
        ipv4_node = self.anm['ipv4'].node(node)
        phy_node = self.anm['phy'].node(node)
        g_ospf = self.anm['ospf']
        g_isis = self.anm['isis']

        super(QuaggaCompiler, self).interfaces(node)
        # OSPF cost
        for interface in node.interfaces:
            ospf_link = g_ospf.edge(
                interface._edge_id)  # find link in OSPF with this ID
            isis_link = g_isis.edge(interface._edge_id) # find link in ISIS with this ID 
# TODO: check finding link if returns cost from r1 -> r2, or r2 -> r1
# (directionality)
            if ospf_link:
                interface['ospf_cost'] = ospf_link.cost

            if isis_link:
                interface['isis'] = True
                isis_node = g_isis.node(node)
                interface['isis_process_id'] = isis_node.process_id  #TODO: should this be from the interface?
                interface['isis_metric'] = isis_link.metric  
                interface['isis_hello'] = isis_link.hello

        if phy_node.is_router:
            node.interfaces.append(
                id=self.lo_interface,
                description="Loopback",
                ipv4_address=ipv4_node.loopback,
                ipv4_subnet=node.loopback_subnet
            )

    def ospf(self, node):
        """Quagga ospf compiler"""
        super(QuaggaCompiler, self).ospf(node)

        # add eBGP link subnets
        g_ipv4 = self.anm['ipv4']
        g_bgp = self.anm['bgp']
        node.ospf.passive_interfaces = []

        for link in g_bgp.edges(node, type="ebgp"):
            nidb_edge = self.nidb.edge(link)
            node.ospf.passive_interfaces.append(
                id=nidb_edge.id,
            )

            ip_link = g_ipv4.edge(link)
            default_ebgp_area = 0
            if not ip_link:
                # TODO: fix this: due to multi edges from router to same switch
                # cluster
                continue
            node.ospf.ospf_links.append(
                network=ip_link.dst.subnet,
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

    def compile(self, node):
        phy_node = self.anm['phy'].node(node)

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
        self.vrf(node)

    def interfaces(self, node):
        ipv4_cidr = ipv6_address = ipv4_address = ipv4_loopback_subnet = None
        if node.ip.use_ipv4:
            ipv4_node = self.anm['ipv4'].node(node)
            ipv4_address = ipv4_node.loopback
            ipv4_loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")
            ipv4_cidr = address_prefixlen_to_network(
                ipv4_address, ipv4_loopback_subnet.prefixlen)
        if node.ip.use_ipv6:
            ipv6_node = self.anm['ipv6'].node(node)
            ipv6_address = address_prefixlen_to_network(
                ipv6_node.loopback, 128)

# TODO: strip out returns from super
        super(IosBaseCompiler, self).interfaces(node)
        # OSPF cost
        g_ospf = self.anm['ospf']
        g_isis = self.anm['isis']

        for interface in node.interfaces:
            ospf_link = g_ospf.edge(
                interface._edge_id)  # find link in OSPF with this ID
            if ospf_link:
                interface['ospf_cost'] = ospf_link.cost
                interface['ospf_use_ivp4'] = node.ospf.use_ipv4
                interface['ospf_use_ivp6'] = node.ospf.use_ipv6
            isis_link = g_isis.edge(
                interface._edge_id)  # find link in OSPF with this ID
            if isis_link:  # only configure if has ospf interface
                interface['isis'] = True
                isis_node = g_isis.node(node)
                interface['isis_process_id'] = isis_node.process_id
                interface['isis_metric'] = isis_link.metric
                interface['isis_use_ivp4'] = node.isis.use_ipv4
                interface['isis_use_ivp6'] = node.isis.use_ipv6

# TODO: update this to new format
        is_isis_node = bool(g_isis.node(node))  # if node is in ISIS graph
        node.interfaces.append(
            id=self.lo_interface,
            description="Loopback",
            ipv4_address=ipv4_address,
            ipv4_subnet=ipv4_loopback_subnet,
            ipv4_cidr=ipv4_cidr,
            ipv6_address=ipv6_address,
            isis=is_isis_node,
            physical=False,
        )

    def bgp(self, node):
        node.bgp.lo_interface = self.lo_interface
        super(IosBaseCompiler, self).bgp(node)

        if node.ip.use_ipv4:
            ipv4_address = self.anm['ipv4'].node(node).loopback
            ipv4_loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")
            ipv4_cidr = address_prefixlen_to_network(
                ipv4_address, ipv4_loopback_subnet.prefixlen)
            node.bgp.ipv4_advertise_subnets = [ipv4_cidr]
        if node.ip.use_ipv6:
            ipv6_node = self.anm['ipv6'].node(node)
            ipv6_address = address_prefixlen_to_network(
                ipv6_node.loopback, 128)
            node.bgp.ipv6_advertise_subnets = [ipv6_address]

        # vrf
        node.bgp.vrfs = []
        vrf_node = self.anm['vrf'].node(node)
        if vrf_node.vrf_role is "PE":
            for vrf in vrf_node.node_vrf_names:
                rd_index = vrf_node.rd_indices[vrf]
                rd = "%s:%s" % (node.loopback, rd_index)
                node.bgp.vrfs.append(
                    vrf=vrf,
                    rd=rd,
                    use_ipv4=node.ip.use_ipv4,
                    use_ipv6=node.ip.use_ipv6,
                )

    def ospf(self, node):
        super(IosBaseCompiler, self).ospf(node)
        for interface in node.interfaces:
            # get ospf info for this id
            ospf_link = self.anm['ospf'].edge(
                interface._edge_id)  # find link in OSPF with this ID
            if ospf_link:
                area = str(ospf_link.area)
                interface['ospf'] = {
                    'area': area,
                    'process_id': node.ospf.process_id,  # from super ospf config
                }

    def vrf(self, node):
        g_vrf = self.anm['vrf']
        vrf_node = self.anm['vrf'].node(node)
        node.vrf.vrfs = []
        if vrf_node.vrf_role is "PE":
            for vrf in vrf_node.node_vrf_names:
                route_target = g_vrf.data.route_targets[node.asn][vrf]
                node.vrf.vrfs.append({
                    'vrf': vrf,
                    'route_target': route_target,
                })

            for interface in node.interfaces:
                vrf_link = self.anm['vrf'].edge(interface._edge_id)
                if vrf_link:
                    interface['vrf'] = vrf_link.vrf # mark interface as being part of vrf

        node.vrf.use_ipv4 = node.ip.use_ipv4
        node.vrf.use_ipv6 = node.ip.use_ipv6
        node.vrf.vrfs.sort("vrf")




    def isis(self, node):
        # TODO: this needs to go into IOS2 for neatness
        """Sets ISIS links
        """
        g_isis = self.anm['isis']
        isis_node = self.anm['isis'].node(node)
        node.isis.net = isis_node.net
        node.isis.process_id = isis_node.process_id
        node.isis.lo_interface = self.lo_interface
        node.isis.isis_links = []

        for interface in node.interfaces:
            isis_link = g_isis.edge(
                interface._edge_id)  # find link in OSPF with this ID
            if isis_link:  # only configure if has ospf interface
                node.isis.isis_links.append(
                    id=interface.id,
                    metric=isis_link.metric,
                )


class IosClassicCompiler(IosBaseCompiler):
    def compile(self, node):
        super(IosClassicCompiler, self).compile(node)

        phy_node = self.anm['phy'].node(node)
        if phy_node.include_csr:
            node.include_csr = True


class Ios2Compiler(IosBaseCompiler):
    def ospf(self, node):
# need to aggregate areas
        super(Ios2Compiler, self).ospf(node)
        g_ospf = self.anm['ospf']

        interfaces_by_area = defaultdict(list)

        for interface in node.interfaces:
            ospf_link = g_ospf.edge(
                interface._edge_id)  # find link in OSPF with this ID
            if ospf_link:
                area = str(ospf_link.area)
                interfaces_by_area[area].append({
                    'id': interface.id,
                    'cost': ospf_link.cost,
                    'passive': False,
                })
        # TODO: make this use the same parameter format as other appends...

        router_area = str(g_ospf.node(node).area)
        interfaces_by_area[router_area].append({
            'id': self.lo_interface,
            'cost': 0,
            'passive': True,
        })

    # and add Loopback with this router's area
        node.ospf.interfaces = dict(
            interfaces_by_area)
        # TODO: workaround for limited wrapping depth,
        # make node.ospf.interfaces grouped by area


class NxOsCompiler(IosBaseCompiler):
    def interfaces(self, node):
# need to aggregate areas
        super(NxOsCompiler, self).interfaces(node)

        for interface in node.interfaces:
            interface['color'] = "red"

    def ospf(self, node):
        super(NxOsCompiler, self).ospf(node)
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
            nidb_node.render.template = "templates/junos.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (
                self.host, "junosphere")
            nidb_node.render.dst_file = "%s.conf" % ank.name_folder_safe(
                phy_node.label)

            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.unit = 0
                edge.id = int_ids.next()

            junos_compiler.compile(nidb_node)


class NetkitCompiler(PlatformCompiler):
    """Netkit Platform Compiler"""
    @staticmethod
    def interface_ids():
        for x in itertools.count(0):
            yield "eth%s" % x

    def compile(self):
        log.info("Compiling Netkit for %s" % self.host)
        g_phy = self.anm['phy']
        quagga_compiler = QuaggaCompiler(self.nidb, self.anm)
# TODO: this should be all l3 devices not just routers
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='quagga'):
            folder_name = naming.network_hostname(phy_node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.base = "templates/quagga"
            nidb_node.render.template = "templates/netkit_startup.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (
                self.host, "netkit")
            nidb_node.render.base_dst_folder = "rendered/%s/%s/%s" % (
                self.host, "netkit", folder_name)
            nidb_node.render.dst_file = "%s.startup" % folder_name

# allocate zebra information
            nidb_node.zebra.password = "1234"
            hostname = folder_name
            if hostname[0] in string.digits:
                hostname = "r" + hostname
            nidb_node.zebra.hostname = hostname  # can't have . in quagga hostnames
            nidb_node.ssh.use_key = True  # TODO: make this set based on presence of key

            # Note this could take external data
            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()
# and allocate tap interface
            nidb_node.tap.id = int_ids.next()

            quagga_compiler.compile(nidb_node)

            # TODO: move these into inherited BGP config
            nidb_node.bgp.debug = True
            static_routes = []
            nidb_node.zebra.static_routes = static_routes

        # and lab.conf
        self.allocate_tap_ips()
        self.lab_topology()

    def allocate_tap_ips(self):
        # TODO: take tap subnet parameter
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
        lab_topology.render_template = "templates/netkit_lab_conf.mako"
        lab_topology.render_dst_folder = "rendered/%s/%s" % (
            self.host, "netkit")
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

        g_ipv4 = self.anm['ipv4']
        lab_topology.config_items = []
        for node in sorted(subgraph.nodes("is_l3device")):
            for edge in node.edges():
                collision_domain = str(
                    g_ipv4.edge(edge).dst.subnet).replace("/", ".")
                numeric_id = edge.id.replace(
                    "eth", "")  # netkit lab.conf uses 1 instead of eth1
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
    to_memory = settings['Compiler']['Cisco']['to memory']

    # def __init__(self, nidb, anm, host):
# TODO: setup to remap allocate interface id function here
        # super(CiscoCompiler, self).__init__(nidb, anm, host)

    @staticmethod
    def interface_ids_ios_by_slot():
        id_pairs = ((slot, 0) for slot in itertools.count(0))
        for (slot, port) in id_pairs:
            # yield "Ethernet%s/%s" % (slot, port)
            yield "GigabitEthernet%s/%s" % (slot, port)

    @staticmethod
    def interface_ids_ios():
        for x in itertools.count(0):
            yield "GigabitEthernet0/%s" % x

    @staticmethod
    def interface_ids_nxos():
        for x in itertools.count(0):
            yield "Ethernet2/%s" % x

    @staticmethod
    def interface_ids_ios2_slot_port():
        """Allocate with slot and port iterating
        """
        id_pairs = ((slot, port) for (
            slot, port) in itertools.product(xrange(17), xrange(5)))
        for (slot, port) in id_pairs:
            yield "GigabitEthernet%s/%s/%s/%s" % (0, 0, slot, port)

    @staticmethod
    def interface_ids_ios2():
        for x in itertools.count(0):
            yield "GigabitEthernet0/0/0/%s" % x

    @staticmethod
    def edge_id_numeric(edge):
        """ Used for sorting
        assumes format xx_src_dst -> return the xx component"""
        try:
            return int(edge.edge_id.split("_")[0])
        except ValueError:
            return edge.edge_id  # not numeric

    def compile(self):
        G_in = self.anm['input']
        G_in_directed = self.anm['input_directed']
        specified_int_names = G_in.data.specified_int_names
        g_phy = self.anm['phy']

        log.info("Compiling Cisco for %s" % self.host)
        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        now = datetime.now()
        if settings['Compiler']['Cisco']['timestamp']:
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            dst_folder = "rendered/%s_%s/%s" % (
                self.host, timestamp, "cisco")  # TODO: use os.path.join
        else:
            dst_folder = "rendered/%s/%s" % (self.host, "cisco")
# TODO: merge common router code, so end up with three loops: routers, ios
# routers, ios2 routers
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/ios.mako"
            if self.to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios()
            int_ids.next()  # 0/0 is used for management ethernet
            for edge in sorted(self.nidb.edges(nidb_node), key=self.edge_id_numeric):
                if specified_int_names:
                    directed_edge = G_in_directed.edge(edge)
                    edge.id = directed_edge.name
                else:
                    edge.id = int_ids.next()

            ios_compiler.compile(nidb_node)

        ios2_compiler = Ios2Compiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios2'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/ios2/router.conf.mako"
            if self.to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios2()
            for edge in sorted(self.nidb.edges(nidb_node), key=self.edge_id_numeric):
                if specified_int_names:
                    directed_edge = G_in_directed.edge(edge)
                    edge.id = directed_edge.name
                else:
                    edge.id = int_ids.next()

            ios2_compiler.compile(nidb_node)

        nxos_compiler = NxOsCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='nx_os'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/nx_os.mako"
            if self.to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_nxos()
            for edge in sorted(self.nidb.edges(nidb_node), key=self.edge_id_numeric):
                if specified_int_names:
                    directed_edge = G_in_directed.edge(edge)
                    edge.id = directed_edge.name
                else:
                    edge.id = int_ids.next()

            nxos_compiler.compile(nidb_node)

        other_nodes = [phy_node for phy_node in g_phy.nodes('is_router', host=self.host)
                       if phy_node.syntax not in ("ios", "ios2")]
        for node in other_nodes:
            phy_node = g_phy.node(node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.input_label = phy_node.id  # set specifically for now for other variants

# TODO: use more os.path.join for render folders
# TODO: Split compilers into seperate modules


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
            nidb_node.render.template = "templates/ios.mako"
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
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()

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
        lab_topology.render_template = "templates/dynagen.mako"
        lab_topology.render_dst_folder = "rendered/%s/%s" % (
            self.host, "dynagen")
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
