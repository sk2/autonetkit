from autonetkit.network_model.link import Link
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.node import Node
from autonetkit.network_model.port import Port
from autonetkit.network_model.topology import Topology
from autonetkit.network_model.types import DeviceType
from autonetkit.workflow.workflow import BaseWorkflow

class PhysicalNode(Node):
    def __init__(self, topology: 'Topology', id):
        super().__init__(topology, id)

        self.testing_val = 123


class PhysicalTopology(Topology[PhysicalNode, Link, Port]):
    pass


class CustomNetworkModel(NetworkModel):
    def __init__(self):
        super().__init__()

        self.test_phy = PhysicalTopology(self, "phy2")


def test_generic_workflow():
    # TODO: see how to specify as return value
    workflow = BaseWorkflow[int]()
    filename = "../../example/small_internet.graphml"
    network_model: CustomNetworkModel = workflow.load(filename, CustomNetworkModel)

    # t_phy = network_model.get_topology("physical")

    workflow.build(network_model)
    t_ebgp = network_model.get_topology("ebgp")
    t_ibgp = network_model.get_topology("ibgp")
    # DO basic check: ebgp and ibgp links should only be setup if rest working
    assert(len(t_ebgp.links()) == 18)
    assert(len(t_ibgp.links()) == 26)

    t2 = network_model.test_phy
    for node in t2.nodes():
        print(node.te)




