from autonetkit.design.layer2 import build_l2, build_l2_conn
from autonetkit.design.routing import build_ospf, build_ebgp, build_ibgp
from autonetkit.design.validation.validation import check_layer2_conn
from autonetkit.network_model.network_model import NetworkModel


class Builder:
    """

    """

    def __init__(self, network_model: NetworkModel):
        self.network_model = network_model

    def build(self) -> None:
        """

        """
        self.build_physical()
        self.build_layer2()
        self.build_ipv4()
        self.build_routing()

    def build_physical(self):
        """

        """
        t_in = self.network_model.get_topology("input")
        t_phy = self.network_model.get_topology("physical")
        t_phy.add_nodes_from(t_in.nodes())
        t_phy.add_links_from(t_in.links())

    def build_layer2(self):
        """

        """
        build_l2(self.network_model)
        build_l2_conn(self.network_model)
        t_l2_conn = self.network_model.get_topology("layer2_conn")
        check_layer2_conn(t_l2_conn)

    def build_ipv4(self):
        """

        """
        import autonetkit.design.ip_addressing.ipv4 as ipv4
        import autonetkit.design.ip_addressing.general as general
        g_ipv4 = self.network_model.create_topology("ipv4")
        general.build_ip_base(self.network_model, g_ipv4)
        general.allocate_asns(g_ipv4)
        ipv4.assign_bc_subnets(g_ipv4)
        general.map_blocks_to_ports(g_ipv4)
        ipv4.assign_loopbacks(g_ipv4)

    def build_routing(self):
        """

        """
        build_ospf(self.network_model)
        build_ibgp(self.network_model)
        build_ebgp(self.network_model)
