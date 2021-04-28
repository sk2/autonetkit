import abc
from typing import Dict

from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.node import Node


class BaseCompiler:
    """

    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def compile(self, network_model: NetworkModel, node: Node) -> Dict:
        """

        @param network_model:
        @param node:
        """
        pass
