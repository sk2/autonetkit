import os
import autonetkit.log as log
from autonetkit.compilers.platform.platform_base import PlatformCompiler
import itertools
import autonetkit.ank as ank
# from autonetkit.compilers.device.
from autonetkit.nidb import ConfigStanza


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
        for phy_node in g_phy.routers(host=self.host, syntax='junos'):
            DmNode = self.nidb.node(phy_node)
            DmNode.add_stanza("render")
            DmNode.render.template = os.path.join("templates", "junos.mako")
            DmNode.render.dst_folder = os.path.join(
                "rendered", self.host, "junosphere")
            DmNode.render.dst_file = "%s.conf" % ank.name_folder_safe(
                phy_node.label)

            int_ids = self.interface_ids()
            for interface in DmNode.physical_interfaces():
                interface.unit = 0
                interface.id = int_ids.next()

            junos_compiler.compile(DmNode)
