import os
import autonetkit.log as log
from autonetkit.compilers.platform.platform_base import PlatformCompiler
import itertools
import autonetkit.ank as ank
#from autonetkit.compilers.device.

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


