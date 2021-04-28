from jinja2 import Template

from autonetkit.design.utils import filters
from autonetkit.design.utils.filters import find_node_by_label
from autonetkit.design.utils.general import group_by
from autonetkit.design.utils.graph_utils import topology_to_nx_graph, wrap_node_ids
from autonetkit.network_model.network_model import NetworkModel
from autonetkit.network_model.types import DeviceType, PortType
from autonetkit.webserver.publish import publish_model_to_webserver

network_model = NetworkModel()

t_phy = network_model.create_topology("physical")

r1 = t_phy.create_node(DeviceType.ROUTER, "r1")
r1.set("x", 0)
r1.set("y", 0)
r1.set("asn", 1)
r2 = t_phy.create_node(DeviceType.ROUTER, "r2")
r3 = t_phy.create_node(DeviceType.ROUTER, "r3")
r4 = t_phy.create_node(DeviceType.ROUTER, "r4")
r5 = t_phy.create_node(DeviceType.ROUTER, "r5")
h1 = t_phy.create_node(DeviceType.HOST, "h1")
h2 = t_phy.create_node(DeviceType.HOST, "h2")

properties = {
    "r2": (250, 0, 1),
    "r3": (0, 250, 1),
    "r4": (250, 250, 1),
    "r5": (500, 125, 2),
    "h1": (125, 125, 1),
    "h2": (500, 250, 2),
}

for node_id, (x, y, asn) in properties.items():
    node = find_node_by_label(t_phy, node_id)
    node.set("x", x)
    node.set("y", y)
    node.set("asn", asn)

# create ports
r1p1 = r1.create_port(PortType.PHYSICAL)
h1p1 = h1.create_port(PortType.PHYSICAL)
# and link them
t_phy.create_link(r1p1, h1p1)

# or create directly
t_phy.create_link(r1.create_port(PortType.PHYSICAL), r2.create_port(PortType.PHYSICAL))
# or in a loop
pairs = [(r1, r2), (r1, r3), (r2, r4),
         (r3, r4), (r2, r5), (r4, r5), (r5, h2)]
for n1, n2 in pairs:
    t_phy.create_link(n1.create_port(PortType.PHYSICAL), n2.create_port(PortType.PHYSICAL))

# create loopbacks
routers = filters.routers(t_phy)
for node in t_phy.nodes():
    lo0 = node.create_port(PortType.LOGICAL)
    node.set("lo0_id", lo0.id)

# assign port labels
for node in t_phy.nodes():
    physical_ports = filters.physical_ports(node)
    for index, port in enumerate(physical_ports):
        port.set("label", f"eth{index}")

t_ip = network_model.create_topology("ip")
t_ip.add_nodes_from(t_phy.nodes())
t_ip.add_links_from(t_phy.links())
grouped = group_by(t_ip.nodes(), "asn")
for asn, nodes in grouped.items():
    for index, node in enumerate(nodes):
        lo0 = node.loopback_zero()
        loopback_ip = f"172.16.{asn}.{index}"
        lo0.set("ip", loopback_ip)

    links = [l for l in t_ip.links()
             if l.n1.get("asn") == l.n2.get("asn") == asn]
    for index, link in enumerate(links):
        prefix = f"10.{asn}.{index}"
        network = prefix + ".0"
        link.p1.set("ip", prefix + ".1")
        link.p1.set("network", network)
        link.p2.set("ip", prefix + ".2")
        link.p2.set("network", network)

# inter-as links
links = [l for l in t_ip.links()
         if l.n1.get("asn") != l.n2.get("asn")]
for index, link in enumerate(links):
    prefix = f"10.0.{index}"
    network = prefix + ".0"
    link.p1.set("ip", prefix + ".1")
    link.p1.set("network", network)
    link.p2.set("ip", prefix + ".2")

t_ospf = network_model.create_topology("ospf")
t_ospf.add_nodes_from(routers)
ebgp_links = [l for l in t_phy.links()
              if l.n1.get("asn") == l.n2.get("asn")]
t_ospf.add_links_from(ebgp_links)

t_ibgp = network_model.create_topology("ibgp")
t_ibgp.add_nodes_from(routers)
ibgp_pairs = [(n1, n2) for n1 in t_ibgp.nodes()
              for n2 in t_ibgp.nodes()
              if n1 != n2 and n1.get("asn") == n2.get("asn")]
for n1, n2 in ibgp_pairs:
    p1 = n1.loopback_zero()
    p2 = n2.loopback_zero()
    t_ibgp.create_link(p1, p2)

t_ebgp = network_model.create_topology("ebgp")
t_ebgp.add_nodes_from(routers)
ebgp_links = [l for l in t_phy.links()
              if l.n1.get("asn") != l.n2.get("asn")]
t_ebgp.add_links_from(ebgp_links)

# analysis
import networkx as nx

graph = topology_to_nx_graph(t_phy)
path = nx.shortest_path(graph, h1.id, h2.id)
path = wrap_node_ids(t_phy, path)

p1 = t_phy.create_node_path(path)

# Compile device models
compiled = {}

for node in filters.routers(t_phy):
    data = {
        "hostname": node.label,
        "interfaces": [],
        "asn": node.get("asn")
    }
    for port in filters.physical_ports(node):
        ip_port = t_ip.get_port_by_id(port.id)
        data["interfaces"].append({
            "id": port.label,
            "ip": ip_port.get("ip")
        })

    ospf_node = t_ospf.get_node_by_id(node.id)
    ospf_enabled = ospf_node.degree() > 0
    data["ospf"] = {"networks": [],
                    "enabled":ospf_enabled}

    for port in filters.physical_ports(ospf_node):
        if not port.connected:
            continue
        ip_port = t_ip.get_port_by_id(port.id)
        network = ip_port.get("network")
        data["ospf"]["networks"].append(network)


    ebgp_node = t_ebgp.get_node_by_id(node.id)
    data["ebgp"] = {"neighbors": []}
    for peer in ebgp_node.peer_nodes():
        ip_peer = t_ip.get_node_by_id(peer.id)
        peer_ip = ip_peer.loopback_zero().get("ip")
        data["ebgp"]["neighbors"].append({
            "ip": peer_ip,
            "asn": peer.get("asn")
        })

    ibgp_node = t_ibgp.get_node_by_id(node.id)
    bgp_enabled = ebgp_node.degree() > 0 or ibgp_node.degree() > 0
    data["bgp_enabled"] = bgp_enabled
    data["ibgp"] = {"neighbors": []}
    for peer in ibgp_node.peer_nodes():
        ip_peer = t_ip.get_node_by_id(peer.id)
        peer_ip = ip_peer.loopback_zero().get("ip")
        data["ibgp"]["neighbors"].append({
            "ip": peer_ip,
            "asn": peer.get("asn")
        })

    compiled[node] = data

for node in filters.hosts(t_phy):
    data = {
        "hostname": node.label,
        "interfaces": []
    }

    for port in filters.physical_ports(node):
        ip_port = t_ip.get_port_by_id(port.id)
        data["interfaces"].append({
            "id": port.label,
            "ip": ip_port.get("ip")
        })

    compiled[node] = data

# and render using template
rtr_template_str = """
! router
hostname {{ data.hostname }}
{% for interface in data.interfaces %}
{{interface.id}} {{ interface.ip}} up
{% endfor %}
{% if data.ospf.enabled %}
!
router ospf
{% for network in data.ospf.networks %}
    network {{network}}
{% endfor %}
!
{% endif %}
{% if data.bgp_enabled %}
router bgp {{ asn }}
{% for peer in data.ebgp.neighbors %}
    neighbor {{peer.ip}} {{peer.asn}}
{% endfor %}
{% for peer in data.ibgp.neighbors %}
    neighbor {{peer.ip}} {{peer.asn}}
{% endfor %}
{% endif %}
!
"""
host_template_str = """
! host
hostname {{ data.hostname }}
{% for interface in data.interfaces %}
{{interface.id}} {{ interface.ip}} up
{% endfor %}
"""

templates = {
    DeviceType.ROUTER: Template(rtr_template_str, trim_blocks=True),
    DeviceType.HOST: Template(host_template_str, trim_blocks=True)
}

for node, data in compiled.items():
    template = templates[node.type]
    rendered = template.render(data=data)
    print(rendered)

publish_model_to_webserver(network_model)
