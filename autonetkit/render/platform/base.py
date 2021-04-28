import abc
from typing import List

from jinja2 import Environment

from autonetkit.network_model.node import Node
from autonetkit.render.types import RenderedFileEntry


class PlatformRenderer:
    """

    """

    def __init__(self, env: Environment):
        self.env: Environment = env

    @abc.abstractmethod
    def render(self, node: Node) -> List[RenderedFileEntry]:
        """

        @param node:
        """
        pass
