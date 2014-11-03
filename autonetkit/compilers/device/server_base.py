#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.log as log
from autonetkit.compilers.device.device_base import DeviceCompiler
from autonetkit.nidb import ConfigStanza


class ServerCompiler(DeviceCompiler):

    def compile(self, node):
        node.do_render = True  # turn on rendering
        phy_node = self.anm['phy'].node(node)
        ipv4_node = self.anm['ipv4'].node(node)
        super(ServerCompiler, self).compile(node)
