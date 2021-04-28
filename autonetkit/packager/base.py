import abc
from typing import Dict

from autonetkit.network_model.network_model import NetworkModel


class AbstractPlatformPackager:
    """

    """

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    @abc.abstractmethod
    def build(self, network_model: NetworkModel) -> Dict:
        """

        @param network_model:
        """
        pass
