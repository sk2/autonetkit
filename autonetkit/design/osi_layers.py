import autonetkit.log as log
import autonetkit.ank as ank_utils

def build_layer2(anm):
    import autonetkit.design.layer2
    autonetkit.design.layer2.build_layer2(anm)
    autonetkit.update_http(anm)

def build_layer3(anm):
    """ l3_connectivity graph: switch nodes aggregated and exploded"""
    g_in = anm['input']
    g_l2 = anm['layer2']
    g_l3 = anm.add_overlay("layer3")
    g_l3.add_nodes_from(g_l2, retain=['label'])
    g_l3.add_nodes_from(g_in.switches(), retain=['asn'])
    g_l3.add_edges_from(g_l2.edges())

    switches = g_l3.switches()

    ank_utils.aggregate_nodes(g_l3, switches)
    exploded_edges = ank_utils.explode_nodes(g_l3,
                                             switches)

    # also explode virtual switches
    vswitches = [n for n in g_l3.nodes()
                 if n['layer2'].device_type == "switch"
                 and n['layer2'].device_subtype == "virtual"]

    # explode each seperately?
    for edge in exploded_edges:
        edge.multipoint = True
        edge.src_int.multipoint = True
        edge.dst_int.multipoint = True
