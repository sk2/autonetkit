import autonetkit.log as log


def  mpls_te(anm):
    g_in = anm['input']
    g_phy = anm['phy']
    # add regardless, so allows quick check of node in anm['ospf'] in compilers
    g_mpls_te = anm.add_overlay("mpls_te")
    if not any(True for n in g_in if n.is_router and n.mpls_te_enabled):
        log.debug("No nodes with mpls_te_enabled set")
        return

    # te head end set if here
    g_mpls_te.add_nodes_from(g_in.routers())

    g_mpls_te.add_edges_from(g_phy.edges())