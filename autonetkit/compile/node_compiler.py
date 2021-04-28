import typing
from typing import Dict

from autonetkit.compile.node.linux_host import LinuxHostCompiler
from autonetkit.compile.node.quagga import QuaggaCompiler

if typing.TYPE_CHECKING:
    from autonetkit.network_model.network_model import NetworkModel
    from autonetkit.network_model.node import Node


class TargetCompilerNotFound(Exception):
    pass


class NodeCompiler:
    """

    """

    def __init__(self):
        self.node_mapping = {
            "quagga": QuaggaCompiler(),
            "linux": LinuxHostCompiler()
        }

    def compile_node(self, network_model: 'NetworkModel', node: 'Node') -> Dict:
        """

        @param network_model:
        @param node:
        @return:
        """
        target = node.get("target")
        try:
            compiler = self.node_mapping[target]
        except KeyError:
            raise TargetCompilerNotFound(target)

        return compiler.compile(network_model, node)
