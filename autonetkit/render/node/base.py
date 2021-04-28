import abc
from typing import Dict

from jinja2 import Environment

from autonetkit.network_model.node import Node


class NodeRenderer:
    """

    """

    def __init__(self, env: Environment):
        self.env: Environment = env

    @abc.abstractmethod
    def render(self, node: Node) -> Dict:
        """

        @param node:
        """
        pass
