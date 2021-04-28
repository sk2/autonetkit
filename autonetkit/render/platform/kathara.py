from typing import Dict, List

from autonetkit.render.platform.base import PlatformRenderer
from autonetkit.render.types import RenderedFileEntry


class KatharaRenderer(PlatformRenderer):
    def render(self, data: Dict) -> List[RenderedFileEntry]:
        """

        @param data:
        @return:
        """
        result = []

        lab_template = self.env.get_template("kathara/lab.conf")
        result.append(RenderedFileEntry(
            lab_template.render(data=data["lab"]),
            None,
            "lab.conf"))

        node_startup_template = self.env.get_template("kathara/node.startup")
        for node in data["nodes"]:
            filename = f"{node['label']}.startup"
            result.append(RenderedFileEntry(
                node_startup_template.render(data=node),
                None,
                filename))

        return result

    def render_node(self, node_data: Dict) -> List[RenderedFileEntry]:
        """

        @param node_data:
        @return:
        """
        result = []

        hostname_template = self.env.get_template("kathara/hostname")
        result.append(RenderedFileEntry(
            hostname_template.render(data=node_data["kathara"]["hostname"]),
            "etc",
            "hostname"))

        shadow_template = self.env.get_template("kathara/shadow")
        result.append(RenderedFileEntry(
            shadow_template.render(),
            "etc",
            "shadow"))

        ssh_template = self.env.get_template("kathara/ssh")
        result.append(RenderedFileEntry(
            ssh_template.render(),
            "etc/ssh",
            "sshd_config"))

        return result
