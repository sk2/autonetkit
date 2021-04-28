from typing import Dict

from autonetkit.compile.node.base import BaseCompiler
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.node import Node


class LinuxHostCompiler(BaseCompiler):
    """

    """

    def __init__(self):
        super().__init__()

        # TODO: assign this at topology load time in pre-process step
        self.lo0_id = "lo:1"

    def compile(self, network_model: NetworkModel, node: Node) -> Dict:
        """

        @param network_model:
        @param node:
        @return:
        """
        # Note: can expand depending on services defined on host, l7 topologies, etc
        return {}
