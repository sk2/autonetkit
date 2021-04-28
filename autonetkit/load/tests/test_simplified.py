import unittest

import autonetkit.load.simplified
from autonetkit.load.common import transform_simplified_to_structured_topology
from autonetkit.load.preprocess import process_structured_topology
from autonetkit.webserver.publish import publish_model_to_webserver


class MyTestCase(unittest.TestCase):
    def test_something(self):
        data = {
            "nodes": [
                {"label": "r1"},
                {"label": "r2"},
                {"label": "r3"},
                {"label": "r4"},
            ],
            "links": [("r1", "r2"), ("r2", "r3"), ("r2", "r4")],
        }
        simplified_topology = autonetkit.load.simplified.SimplifiedTopology(**data)

        topology = transform_simplified_to_structured_topology(simplified_topology)

        network_model = process_structured_topology(topology)
        publish_model_to_webserver(network_model)


if __name__ == '__main__':
    unittest.main()
