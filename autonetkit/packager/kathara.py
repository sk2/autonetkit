import logging
import os

from autonetkit.compile.node_compiler import TargetCompilerNotFound, NodeCompiler
from autonetkit.compile.platform.kathara import KatharaCompiler
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.packager.base import AbstractPlatformPackager
from autonetkit.packager.utils import write_rendered_to_file
from autonetkit.render.exceptions import RenderException
from autonetkit.render.platform.kathara import KatharaRenderer
from autonetkit.render.renderer import Renderer

logger = logging.getLogger(__name__)


class KatharaPlatformPackager(AbstractPlatformPackager):
    """

    """

    def __init__(self):
        # TODO: allow passing in lab metadata (name, description, etc) info also
        super().__init__()

    def build(self, network_model: NetworkModel) -> None:
        """

        @param network_model:
        """
        compiler = NodeCompiler()
        renderer = Renderer()

        base_dir = os.path.join(self.output_dir, "lab")
        try:
            os.mkdir(base_dir)
        except FileExistsError:
            pass
        except FileNotFoundError as err:
            raise RenderException(err)

        self._compile_nodes(base_dir, compiler, network_model, renderer)
        self._compile_platform(base_dir, network_model, renderer)

    def _compile_nodes(self, base_dir, compiler, network_model, renderer):
        platform_compiler = KatharaCompiler()
        platform_renderer = KatharaRenderer(renderer.env)
        for node in network_model.get_topology("physical").nodes():
            try:
                node_data = compiler.compile_node(network_model, node)
            except TargetCompilerNotFound:
                logger.warning("No compiler defined for %s", node.label)
                continue

            target = node.get("target")
            rendered = renderer.render_node(node_data, target)

            # TODO: add hostname as platform specific extra renderer
            node_data["kathara"] = {
                "hostname": platform_compiler.compile_node(node)
            }

            # also append kathara specific files to allow ssh into node
            # Note: these don't need compilation
            rendered += platform_renderer.render_node(node_data)

            node_dir = os.path.join(base_dir, node.label)
            try:
                os.mkdir(node_dir)
            except FileExistsError:
                pass

            for entry in rendered:
                write_rendered_to_file(entry, node_dir)

    def _compile_platform(self, base_dir, network_model, renderer):
        platform_compiler = KatharaCompiler()
        platform_data = platform_compiler.compile(network_model)
        platform_renderer = KatharaRenderer(renderer.env)
        rendered = platform_renderer.render(platform_data)
        for entry in rendered:
            write_rendered_to_file(entry, base_dir)
