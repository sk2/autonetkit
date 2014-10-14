import autonetkit
import autonetkit.design.igp
from mock import patch

def build_layer3():
    anm = autonetkit.topos.house()
    from autonetkit.design.osi_layers import build_layer2, build_layer3
    build_layer2(anm)
    build_layer3(anm)


    return anm


def test_ospf():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True

    for node in anm['phy']:
        node.igp = "ospf"

    autonetkit.design.igp.build_ospf(anm)

    g_ospf = anm['ospf']
    assert(len(g_ospf) == 5)
    edges = {(e.src, e.dst) for e in g_ospf.edges()}
    expected = {("r4", "r5"), ("r1", "r2"), ("r1", "r3"), ("r2", "r3")}
    assert edges == expected


def test_ospf_no_routing():
    anm = build_layer3()
    autonetkit.design.igp.build_ospf(anm)

def test_ospf_no_isis_set():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True
    autonetkit.design.igp.build_ospf(anm)

def test_eigrp():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True

    for node in anm['phy']:
        node.igp = "eigrp"

    autonetkit.design.igp.build_eigrp(anm)

    g_eigrp = anm['eigrp']
    assert(len(g_eigrp) == 5)
    edges = {(e.src, e.dst) for e in g_eigrp.edges()}
    expected = {("r4", "r5"), ("r1", "r2"), ("r1", "r3"), ("r2", "r3")}
    assert edges == expected

def test_eigrp_no_routing():
    anm = build_layer3()
    autonetkit.design.igp.build_eigrp(anm)

def test_eigrp_no_isis_set():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True
    autonetkit.design.igp.build_eigrp(anm)

def net_side_effect(anm):
    import netaddr
    g_isis = anm['isis']
    #Note: this only mocks up to 255
    import itertools
    # fake the NET addresses
    nets = ("49.1921.6801.%s.00" % x for x in itertools.count(start=9001))
    for node in g_isis:
        node.net =nets.next()

def test_isis():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True

    # isis also needs ipv4 to allocate the OSI addresses

    for node in anm['phy']:
        node.igp = "isis"

#@patch("", side_effect=net_side_effect)
    with patch("autonetkit.design.igp.build_network_entity_title",
        side_effect = net_side_effect):
        autonetkit.design.igp.build_isis(anm)

    g_isis = anm['isis']
    assert(len(g_isis) == 5)
    edges = {(e.src, e.dst) for e in g_isis.edges()}
    expected = {("r4", "r5"), ("r1", "r2"), ("r1", "r3"), ("r2", "r3")}
    assert edges == expected

def test_isis_no_routing():
    anm = build_layer3()
    autonetkit.design.igp.build_isis(anm)

def test_isis_no_isis_set():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True
    autonetkit.design.igp.build_isis(anm)

def test_multi_igp():
    anm = build_layer3()
    anm['phy'].data.enable_routing = True
    g_phy = anm['phy']

    igps = {"r1": "ospf", "r2": "ospf", "r3": "ospf", "r4": "isis", "r5": "isis"}
    for label, igp in igps.items():
        g_phy.node(label).igp = igp

    with patch("autonetkit.design.igp.build_network_entity_title",
        side_effect = net_side_effect):
        autonetkit.design.igp.build_igp(anm)

    g_ospf = anm['ospf']
    g_isis = anm['isis']
    assert(len(g_ospf) == 3)
    assert(len(g_isis) == 2)
    edges = {(e.src, e.dst) for e in g_ospf.edges()}
    expected = {("r1", "r2"), ("r1", "r3"), ("r2", "r3")}
    assert edges == expected

    edges = {(e.src, e.dst) for e in g_isis.edges()}
    expected = {("r4", "r5")}
    assert edges == expected

    #TODO: check labels in the merged g_igp graph

test_multi_igp()