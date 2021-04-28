from typing import Dict, List

from autonetkit.render.node.base import NodeRenderer
from autonetkit.render.types import RenderedFileEntry


class QuaggaRenderer(NodeRenderer):
    def render(self, data: Dict) -> List[RenderedFileEntry]:
        """

        @param data:
        @return:
        """
        result = []
        quagga_path = "etc/quagga"

        zebra_template = self.env.get_template("quagga/zebra.conf")
        result.append(RenderedFileEntry(
            zebra_template.render(node=data),
            quagga_path,
            "zebra.conf"))

        ospfd_template = self.env.get_template("quagga/ospfd.conf")
        result.append(RenderedFileEntry(
            ospfd_template.render(node=data),
            quagga_path,
            "ospfd.conf"))

        bgpd_template = self.env.get_template("quagga/bgpd.conf")
        result.append(RenderedFileEntry(
            bgpd_template.render(node=data),
            quagga_path,
            "bgpd.conf"))

        daemons_template = self.env.get_template("quagga/daemons.conf")
        result.append(RenderedFileEntry(
            daemons_template.render(node=data),
            quagga_path,
            "daemons.conf"))

        return result
