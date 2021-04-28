from typing import Dict, List

from autonetkit.render.node.base import NodeRenderer
from autonetkit.render.types import RenderedFileEntry


class LinuxHostRenderer(NodeRenderer):
    def render(self, data: Dict) -> List[RenderedFileEntry]:
        """

        @param data:
        @return:
        """
        # Note: Can fill in once hosts setup
        result = []
        return result
