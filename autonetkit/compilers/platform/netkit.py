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
from autonetkit.nidb import ConfigStanza
from autonetkit.render2 import NodeRender, PlatformRender


class NetkitCompiler(PlatformCompiler):

    """Netkit Platform Compiler"""
    @staticmethod
    def index_to_int_id(index):
        """Maps interface index to ethx e.g. eth0, eth1, ..."""
        return "eth%s" % index

    def compile(self):
        self.copy_across_ip_addresses()

        log.info("Compiling Netkit for %s" % self.host)
        g_phy = self.anm['phy']
        quagga_compiler = QuaggaCompiler(self.nidb, self.anm)

        # todo: set platform render
        lab_topology = self.nidb.topology(self.host)
        lab_topology.render2 = PlatformRender()

# TODO: this should be all l3 devices not just routers
        for phy_node in g_phy.l3devices(host=self.host, syntax='quagga'):
            folder_name = naming.network_hostname(phy_node)
            dm_node = self.nidb.node(phy_node)
            dm_node.add_stanza("render")
            # TODO: order by folder and file template src/dst
            dm_node.render.base = os.path.join("templates", "quagga")
            dm_node.render.template = os.path.join("templates",
                                                   "netkit_startup.mako")
            dm_node.render.dst_folder = os.path.join("rendered",
                                                     self.host, "netkit")
            dm_node.render.base_dst_folder = os.path.join("rendered",
                                                          self.host, "netkit", folder_name)
            dm_node.render.dst_file = "%s.startup" % folder_name

            dm_node.render.custom = {
                'abc': 'def.txt'
            }

            render2 = NodeRender()
            # TODO: dest folder also needs to be able to accept a list
            # TODO: document that use a list so can do native os.path.join on
            # target platform
            render2.add_folder(["templates", "quagga"], folder_name)
            render2.add_file(
                ("templates", "netkit_startup.mako"), "%s.startup" % folder_name)
            dm_node.render2 = render2
            lab_topology.render2.add_node(dm_node)
            # lab_topology.render2_hosts.append(phy_node)

# allocate zebra information
            dm_node.add_stanza("zebra")
            if dm_node.is_router():
                dm_node.zebra.password = "1234"
            hostname = folder_name
            if hostname[0] in string.digits:
                hostname = "r" + hostname
            dm_node.hostname = hostname  # can't have . in quagga hostnames
            dm_node.add_stanza("ssh")
            # TODO: make this set based on presence of key
            dm_node.ssh.use_key = True

            # Note this could take external data
            int_ids = itertools.count(0)
            for interface in dm_node.physical_interfaces():
                numeric_id = int_ids.next()
                interface.numeric_id = numeric_id
                interface.id = self.index_to_int_id(numeric_id)

# and allocate tap interface
            dm_node.add_stanza("tap")
            dm_node.tap.id = self.index_to_int_id(int_ids.next())

            quagga_compiler.compile(dm_node)

            if dm_node.bgp:
                dm_node.bgp.debug = True
                static_routes = []
                dm_node.zebra.static_routes = static_routes

        # and lab.conf
        self.allocate_tap_ips()
        self.allocate_lab_topology()

    def allocate_tap_ips(self):
        """Allocates TAP IPs"""
        settings = autonetkit.config.settings
        lab_topology = self.nidb.topology(self.host)
        from netaddr import IPNetwork
        address_block = IPNetwork(settings.get("tapsn")
                                  or "172.16.0.0/16").iter_hosts()  # added for backwards compatibility
        lab_topology.tap_host = address_block.next()
        lab_topology.tap_vm = address_block.next()  # for tunnel host
        for node in sorted(self.nidb.l3devices(host=self.host)):
            node.tap.ip = address_block.next()

    def allocate_lab_topology(self):
        # TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology(self.host)
        lab_topology.render_template = os.path.join("templates",
                                                    "netkit_lab_conf.mako")
        lab_topology.render_dst_folder = os.path.join("rendered",
                                                      self.host, "netkit")
        lab_topology.render_dst_file = "lab.conf"
        lab_topology.description = "AutoNetkit Lab"
        lab_topology.author = "AutoNetkit"
        lab_topology.web = "www.autonetkit.org"

        render2 = lab_topology.render2
        # TODO: test with adding a folder
        #render2.add_folder(["templates", "quagga"], folder_name)
        render2.add_file(("templates", "netkit_lab_conf.mako"), "lab.conf")
        render2.base_folder = [self.host, "netkit"]
        render2.archive = "%s_%s" % (self.host, "netkit")
        render2.template_data = {
            "render_dst_file": "lab.conf",
            "description": "AutoNetkit Lab",
            "author": "AutoNetkit",
            "web": "www.autonetkit.org",
        }

        host_nodes = list(
            self.nidb.nodes(host=self.host, platform="netkit"))
        if not len(host_nodes):
            log.debug("No Netkit hosts for %s" % self.host)
# also need collision domains for this host
        cd_nodes = self.nidb.nodes("broadcast_domain", host=self.host)
        host_nodes += cd_nodes
        subgraph = self.nidb.subgraph(host_nodes, self.host)

        lab_topology.machines = " ".join(alpha_sort(naming.network_hostname(phy_node)
                                                    for phy_node in subgraph.l3devices()))

        lab_topology.config_items = []
        for node in sorted(subgraph.l3devices()):
            for interface in node.physical_interfaces():
                broadcast_domain = str(interface.ipv4_subnet).replace("/", ".")
                # netkit lab.conf uses 1 instead of eth1
                numeric_id = interface.numeric_id
                stanza = ConfigStanza(
                    device=naming.network_hostname(node),
                    key=numeric_id,
                    value=broadcast_domain,
                )
                lab_topology.config_items.append(stanza)

        lab_topology.tap_ips = []
        for node in subgraph:
            if node.tap:
                stanza = ConfigStanza(
                    device=naming.network_hostname(node),
                    id=node.tap.id.replace("eth", ""),  # strip ethx -> x
                    ip=node.tap.ip,
                )
                lab_topology.tap_ips.append(stanza)

        lab_topology.tap_ips = sorted(lab_topology.tap_ips, key=lambda x: x.ip)
        lab_topology.config_items = sorted(
            lab_topology.config_items, key=lambda x: x.device)
