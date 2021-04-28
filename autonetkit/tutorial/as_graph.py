from autonetkit.design.utils.graph_utils import force_layout
from autonetkit.load.common import build_model_from_nx_graph
from autonetkit.workflow.workflow import BaseWorkflow


def main():
    """

    """
    workflow = BaseWorkflow()

    import networkx as nx
    graph = nx.random_internet_as_graph(100)
    network_model = build_model_from_nx_graph(graph)
    t_in = network_model.get_topology("input")

    asn = 1
    for node_id, data in graph.nodes(data=True):
        node = t_in.get_node_by_id(str(node_id))
        node.set("role", data["type"])
        node.set("asn", asn)
        asn += 1

    t_in = network_model.get_topology("input")
    force_layout(t_in, scale=500)
    workflow.run(network_model, target_platform="kathara")


if __name__ == '__main__':
    main()
