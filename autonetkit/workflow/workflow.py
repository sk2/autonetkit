from autonetkit.design.builder import Builder
from autonetkit.load.load_graphml import import_from_graphml
from autonetkit.load.validation import validate
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.packager.mapping import get_platform_builder
from autonetkit.webserver.publish import publish_model_to_webserver


class BaseWorkflow:
    """

    """

    def __init__(self):
        pass

    def run(self, network_model: NetworkModel, target_platform: str):
        """

        @param network_model:
        @param target_platform:
        """
        t_in = network_model.get_topology("input")
        validate(t_in)
        self.build(network_model)
        self.render(network_model, target_platform)
        self.publish(network_model)

    @staticmethod
    def load(input_file):
        """

        @param input_file:
        @return:
        """
        network_model = import_from_graphml(input_file)
        return network_model

    @staticmethod
    def publish(network_model):
        """

        @param network_model:
        """
        host = "http://0.0.0.0:8080"
        publish_model_to_webserver(network_model, host)

    @staticmethod
    def build(network_model):
        """

        @param network_model:
        """
        builder = Builder(network_model)
        builder.build()

    @staticmethod
    def render(network_model, target_platform):
        """

        @param network_model:
        @param target_platform:
        """
        builder = get_platform_builder(target_platform)
        builder.build(network_model)
