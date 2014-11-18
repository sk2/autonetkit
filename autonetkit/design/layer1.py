import autonetkit.ank as ank_utils
import autonetkit.log as log

def build_layer1(anm):
    g_l1 = anm.add_overlay('layer1')
    g_phy = anm['phy']
    g_l1.add_nodes_from(g_phy)
    g_l1.add_edges_from(g_phy.edges())

    # aggregate collision domains



#TODO: build layer 1 connectivity graph