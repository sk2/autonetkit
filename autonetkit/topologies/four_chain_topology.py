def four_chain():
    """Returns anm with  input and physical as house graph"""
    import autonetkit
    anm = autonetkit.NetworkModel()

    g_in = anm.add_overlay("input")

    router_ids = ["r1", "r2", "r3", "r4"]
    g_in.add_nodes_from(router_ids)

    g_in.update(device_type = "router")
    g_in.update(asn = 1)

    positions = {'r1': (101, 250), 'r2': (100, 500), 'r3': (100, 750), 'r4': (100, 1000)}
    for node in g_in:
        node.x = positions[node][0]
        node.y = positions[node][1]
        eth0 = node.add_interface("eth0")
        eth0.speed = 100

    # node->node edges
    input_edges = [("r1", "r2"), ("r2", "r4"), ("r3", "r4")]
    input_interface_edges = [(g_in.node(src).interface(1), g_in.node(dst).interface(1)) for src, dst in input_edges]
    g_in.add_edges_from(input_interface_edges)

    g_phy = anm['phy']
    g_phy.add_nodes_from(g_in, retain=["device_type", "x", "y", "asn"])
    g_phy.add_edges_from(g_in.edges())

    return anm
