import json
import logging

import requests

from autonetkit.common.utils import CustomJsonEncoder

logger = logging.getLogger(__name__)


def publish_model_to_webserver(network_model, host="http://0.0.0.0:8080"):
    """

    @param network_model:
    @param host:
    @return:
    """
    exported = network_model.export()
    exported_json = json.dumps(exported, cls=CustomJsonEncoder, indent=4)
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
