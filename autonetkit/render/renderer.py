from typing import Dict, List

from jinja2 import Environment, PackageLoader

from autonetkit.render.exceptions import RendererNotDefined
from autonetkit.render.node.linux_host import LinuxHostRenderer
from autonetkit.render.node.quagga import QuaggaRenderer
from autonetkit.render.types import RenderedFileEntry


class Renderer:
    """

    """

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader('autonetkit', 'render/templates'),
            trim_blocks=True, lstrip_blocks=True
        )

        self.target_map = {
            "quagga": QuaggaRenderer(self.env),
            "linux": LinuxHostRenderer(self.env)
        }

    def render_node(self, compiled_data: Dict, target: str) -> List[RenderedFileEntry]:
        """

        @param compiled_data:
        @param target:
        @return:
        """
        try:
            renderer = self.target_map[target]
        except KeyError:
            raise RendererNotDefined(target)

        return renderer.render(compiled_data)
