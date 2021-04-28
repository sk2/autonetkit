import abc
from typing import Dict

from autonetkit.network_model.network_model import NetworkModel


class BasePlatformCompiler:
    """

    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def compile(self, network_model: NetworkModel) -> Dict:
        """

        @param network_model:
        """
        pass
