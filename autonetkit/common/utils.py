import ipaddress
import json
from enum import Enum

from autonetkit.network_model.base.topology_element import TopologyElement, BaseTopology


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        """

        @param obj:
        @return:
        """
        if isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, TopologyElement):
            return obj.id
        elif isinstance(obj, BaseTopology):
            return obj.id
        elif isinstance(obj, ipaddress.IPv4Network):
            return str(obj)
        elif isinstance(obj, ipaddress.IPv4Address):
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)