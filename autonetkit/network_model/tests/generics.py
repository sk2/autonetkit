import json
import pprint
from dataclasses import dataclass
from typing import Optional

from autonetkit.common.utils import CustomJsonEncoder
from autonetkit.network_model.base.import_export import restore_topology
from autonetkit.network_model.base.link import Link
from autonetkit.network_model.base.network_model import NetworkModel
from autonetkit.network_model.base.node import Node
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.topology import Topology
from autonetkit.network_model.base.types import DeviceType, PortType
from autonetkit.webserver.publish import publish_model_to_webserver
from autonetkit.workflow.workflow import BaseWorkflow

# TODO: extend the code for NodePaths and PortPaths


PT = 'PhysicalTopology'
PL = 'PhysicalLink'
PP = 'PhysicalPort'
PN = 'PhysicalNode'


# TODO: document that should set defaults in init -> not on the class variable itself
# TODO: document that must set the type or it wont be imported/exported

@dataclass
class PhysicalNode(Node[PT, PL, PP]):
    link_test: Optional[PL] = None
    val92: str = None
    port_test: PP = None
    test3: int = 123
    testing_val = 123
    val2: int = 122333


@dataclass
class PhysicalLink(Link[PT, PN, PP]):
    link_test = 345
    link_bc = 21


@dataclass
class PhysicalPort(Port[PT, PL, PP]):
    port_test: float = 567


@dataclass
class PhysicalTopology(Topology[PN, PL, PP]):
    _node_cls = PhysicalNode
    _link_cls = PhysicalLink
    _port_cls = PhysicalPort


@dataclass
class CustomNetworkModel(NetworkModel):
    test_phy: PhysicalTopology = None
    test2 = 123


# import pprint
# pprint.pprint(dataclasses.fields(PhysicalNode))
# print("---")


def test_generic_workflow():
    # TODO: see how to specify as return value
    workflow = BaseWorkflow()
    filename = "../../example/small_internet.graphml"
    network_model: CustomNetworkModel = workflow.load(filename, CustomNetworkModel)
    network_model.create_topology("1234")

    t_phy3 = network_model.test_phy

    t_phy3.create_node(DeviceType.ROUTER)

    # print(t_base.id)
    # print(t_phy3.id)
    #
    # for node in t_phy3.nodes():
    #     print("HERE type", type(node))

    # t_phy = network_model.get_topology("physical")

    workflow.build(network_model)

    t_phy = network_model.get_topology("physical")

    t_ebgp = network_model.get_topology("ebgp")
    t_ibgp = network_model.get_topology("ibgp")
    # DO basic check: ebgp and ibgp links should only be setup if rest working
    assert (len(t_ebgp.links()) == 18)

    assert (len(t_ibgp.links()) == 26)

    r1 = network_model.test_phy.create_node(DeviceType.ROUTER, "r1")
    r1.set("x", 100)
    r1.set("y", 100)
    r2 = network_model.test_phy.create_node(DeviceType.ROUTER, "r2")

    # r1.val2 = "def"
    # print(r1.val2)
    r1.test3 = 23444544
    r1.test_inside = 999

    p1 = r1.create_port(PortType.PHYSICAL)
    p2 = r2.create_port(PortType.PHYSICAL)
    l1 = network_model.test_phy.create_link(p1, p2)
    l1.link_test = 2333332

    # test advanced annotations
    r1.port_test = p1
    r2.port_test = p2
    r1.link_test = l1
    r2.link_test = l1

    # copy nodes into test phy
    network_model.test_phy.add_nodes_from(t_phy.nodes())
    print("test nodes", network_model.test_phy.nodes())

    publish_model_to_webserver(network_model)
    # import_data(r1, {"test3": 50})

    exported = network_model.export()

    data = json.dumps(exported, cls=CustomJsonEncoder, indent=2)

    # with open("test.json", "w") as fh:
    #     fh.write(data)

    parsed = json.loads(data)

    pprint.pprint(parsed["test_phy"])

    # test casting - this should be cast to an int
    parsed["test_phy"]["nodes"]["n34"]["test3"] = "12345"

    nm2 = restore_topology(CustomNetworkModel, parsed)

    # export now
    exported2 = nm2.export()

    assert exported2["test_phy"]["nodes"]["n34"]["test3"] != "12345"
    assert exported2["test_phy"]["nodes"]["n34"]["test3"] == 12345

    # get items
    nm2_r1 = nm2.test_phy.get_node_by_id(r1.id)
    print(nm2_r1, nm2_r1.link_test)

    pprint.pprint(exported2["test_phy"])

    t2 = network_model.test_phy
    # for node in t2.nodes():
    #     print(node.val2, node.type, node.test3)
    #     for port in node.ports():
    #         print(port, port, port.port_test)
    #
    # for link in t2.links():
    #     print("link", link, link.n1.val2, link.link_test)

    # exported = network_model.export()
    # print(json.dumps(exported, default=str, indent=2))
