import ipaddress
import json
import logging
from enum import Enum

import requests

logger = logging.getLogger(__name__)


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        """

        @param obj:
        @return:
        """
        if isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, ipaddress.IPv4Network):
            return str(obj)
        elif isinstance(obj, ipaddress.IPv4Address):
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def publish_model_to_webserver(network_model, host="http://0.0.0.0:8080"):
    """

    @param network_model:
    @param host:
    @return:
    """
    exported = network_model.export()
    exported_json = json.dumps(exported, cls=ComplexEncoder, indent=4)
    try:
        result = requests.post(f"{host}/data", data=exported_json)
    except requests.exceptions.ConnectionError:
        logger.warning("Unable to post data to server: %s", host)
        return

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.warning(err)
    else:
        logger.info("Published to webserver")
