import autonetkit.log as log


def  mpls_te(anm):
    g_in = anm['input']
    g_phy = anm['phy']
    g_l3_conn = anm['l3_conn']
    # add regardless, so allows quick check of node in anm['ospf'] in compilers
    g_mpls_te = anm.add_overlay("mpls_te")
    if not any(True for n in g_in if n.is_router and n.mpls_te_enabled):
        log.debug("No nodes with mpls_te_enabled set")
        return

    # te head end set if here
    g_mpls_te.add_nodes_from(g_in.routers())
    # build up edge list sequentially, to provide meaningful messages for multipoint links

    multipoint_edges = [e for e in g_l3_conn.edges()
        if e.multipoint]
    log.info("Excluding multi-point edges from MPLS TE topology: %s"
        % ", ".join(str(e) for e in multipoint_edges))

    edges_to_add = set(g_l3_conn.edges()) - set(multipoint_edges)
    g_mpls_te.add_edges_from(edges_to_add)