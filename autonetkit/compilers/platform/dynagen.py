import os
import autonetkit.log as log
from autonetkit.compilers.platform.platform_base import PlatformCompiler
import itertools
import autonetkit.ank as ank
from autonetkit.compilers.device.cisco import IosClassicCompiler

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
