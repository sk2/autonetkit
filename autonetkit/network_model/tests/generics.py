from autonetkit.network_model.base.link import Link
from autonetkit.network_model.base.network_model import NetworkModel
from autonetkit.network_model.base.node import Node
from autonetkit.network_model.base.port import Port
from autonetkit.network_model.base.topology import Topology
from autonetkit.network_model.base.types import DeviceType, PortType
from autonetkit.workflow.workflow import BaseWorkflow


#TODO: extend the code for NodePaths and PortPaths

class PhysicalNode(Node['PhysicalTopology', 'PhysicalLink', 'PhysicalPort']):
    def __init__(self, topology: 'Topology', id):
        super().__init__(topology, id)
        self.testing_val = 123
        self.val2: int = 122333


class PhysicalLink(Link['PhysicalTopology', 'PhysicalNode', 'PhysicalPort']):
    def __init__(self, topology, id, p1: 'P', p2: 'P'):
        super().__init__(topology, id, p1, p2)
        self.link_test = 345


class PhysicalPort(Port['PhysicalTopology', 'PhysicalLink', 'PhysicalPort']):
    def __init__(self, node: 'Node', id):
        super().__init__(node, id)
        self.port_test = 567


class PhysicalTopology(Topology['PhysicalNode', 'PhysicalLink', 'PhysicalPort']):
    _node_cls = PhysicalNode
    _link_cls = PhysicalLink
    _port_cls = PhysicalPort


class CustomNetworkModel(NetworkModel):
    def __init__(self):
        super().__init__()

        self.test_phy = PhysicalTopology(self, "phy2")
        self.test2 = 123


def test_generic_workflow():
    # TODO: see how to specify as return value
    workflow = BaseWorkflow[CustomNetworkModel]()
    filename = "../../example/small_internet.graphml"
    network_model: CustomNetworkModel = workflow.load(filename, CustomNetworkModel)
    network_model.create_topology("1234")

    # t_phy = network_model.get_topology("physical")

    workflow.build(network_model)
    t_ebgp = network_model.get_topology("ebgp")
    t_ibgp = network_model.get_topology("ibgp")
    # DO basic check: ebgp and ibgp links should only be setup if rest working
    assert (len(t_ebgp.links()) == 18)

    assert (len(t_ibgp.links()) == 26)

    r1 = network_model.test_phy.create_node(DeviceType.ROUTER, "r1")
    r2 = network_model.test_phy.create_node(DeviceType.ROUTER, "r2")
    r1.val2 = "def"

    l1 = network_model.test_phy.create_link(r1.create_port(PortType.PHYSICAL), r2.create_port(PortType.PHYSICAL))
    l1.link_test = 2333332

    t2 = network_model.test_phy
    for node in t2.nodes():
        print(node.val2, node.type)
        for port in node.ports():
            print(port, port)

    for link in t2.links():
        print("link", link, link.n1.val2, link.link_test)

    exported = network_model.export()
    import pprint
    pprint.pprint(exported)
