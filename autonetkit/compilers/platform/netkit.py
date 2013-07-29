"""Compiler for Netkit"""
import os
import autonetkit
import autonetkit.config
import autonetkit.log as log
import autonetkit.plugins.naming as naming
from autonetkit.compilers.platform.platform_base import PlatformCompiler
import string
import itertools
from autonetkit.ank_utils import alphabetical_sort as alpha_sort
from autonetkit.compilers.device.quagga import QuaggaCompiler

class NetkitCompiler(PlatformCompiler):
    """Netkit Platform Compiler"""
    @staticmethod
    def index_to_int_id(index):
        """Maps interface index to ethx e.g. eth0, eth1, ..."""
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
            nidb_node.render.template = os.path.join("templates",
                "netkit_startup.mako")
            nidb_node.render.dst_folder = os.path.join("rendered",
                self.host, "netkit")
            nidb_node.render.base_dst_folder = os.path.join("rendered",
                self.host, "netkit", folder_name)
            nidb_node.render.dst_file = "%s.startup" % folder_name

            nidb_node.render.custom = {
                    'abc': 'def.txt'
                    }

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

            if nidb_node.bgp:
                nidb_node.bgp.debug = True
                static_routes = []
                nidb_node.zebra.static_routes = static_routes

        # and lab.conf
        self.allocate_tap_ips()
        self.lab_topology()

    def allocate_tap_ips(self):
        """Allocates TAP IPs"""
        settings = autonetkit.config.settings
        lab_topology = self.nidb.topology[self.host]
        from netaddr import IPNetwork
        address_block = IPNetwork(settings.get("tapsn")
            or "172.16.0.0/16").iter_hosts() # added for backwards compatibility
        lab_topology.tap_host = address_block.next()
        lab_topology.tap_vm = address_block.next()  # for tunnel host
        for node in sorted(self.nidb.nodes("is_l3device", host=self.host)):
            node.tap.ip = address_block.next()

    def lab_topology(self):
# TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology[self.host]
        lab_topology.render_template = os.path.join("templates",
            "netkit_lab_conf.mako")
        lab_topology.render_dst_folder = os.path.join("rendered",
            self.host, "netkit")
        lab_topology.render_dst_file = "lab.conf"
        lab_topology.description = "AutoNetkit Lab"
        lab_topology.author = "AutoNetkit"
        lab_topology.web = "www.autonetkit.org"
        host_nodes = list(
            self.nidb.nodes(host=self.host, platform="netkit"))
        if not len(host_nodes):
            log.debug("No Netkit hosts for %s" % self.host)
# also need collision domains for this host
        cd_nodes = self.nidb.nodes("collision_domain", host=self.host)
        host_nodes += cd_nodes
        subgraph = self.nidb.subgraph(host_nodes, self.host)

        lab_topology.machines = " ".join(alpha_sort(naming.network_hostname(phy_node)
            for phy_node in subgraph.nodes("is_l3device")))

        lab_topology.config_items = []
        for node in sorted(subgraph.nodes("is_l3device")):
            for interface in node.physical_interfaces:
                collision_domain = str(interface.ipv4_subnet).replace("/", ".")
                #netkit lab.conf uses 1 instead of eth1
                numeric_id = interface.numeric_id
                lab_topology.config_items.append(
                    device=naming.network_hostname(node),
                    key=numeric_id,
                    value=collision_domain,
                )

        lab_topology.tap_ips = []
        for node in subgraph:
            if node.tap:
                lab_topology.tap_ips.append(
                    device=naming.network_hostname(node),
                    id=node.tap.id.replace("eth", ""),  # strip ethx -> x
                    ip=node.tap.ip,
                )

        lab_topology.tap_ips.sort("ip")
        lab_topology.config_items.sort("device")

