#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit.ank as ank_utils
import autonetkit.config
import autonetkit.log as log

SETTINGS = autonetkit.config.settings


# TODO: refactor to go in chronological workflow order




#@call_log
def build_ip(anm):
    g_ip = anm.add_overlay('ip')
    g_l2_bc = anm['layer2_bc']
    # Retain arbitrary ASN allocation for IP addressing
    g_ip.add_nodes_from(g_l2_bc, retain=["asn", "broadcast_domain"])
    g_ip.add_edges_from(g_l2_bc.edges())

    #TODO:
    for bc in g_ip.nodes("broadcast_domain"):
        bc.allocate = True

    for bc in g_ip.nodes("broadcast_domain"):
        # Encapsulated if any neighbor interface has
        for edge in bc.edges():
            if edge.dst_int['phy'].l2_encapsulated:
                log.debug("Removing IP allocation for broadcast_domain %s "
                         "as neighbor %s is L2 encapsulated", bc, edge.dst)

                #g_ip.remove_node(bc)
                bc.allocate = False

                break


def build_ipv4(anm, infrastructure=True):
    import autonetkit.design.ip_addressing.ipv4
    autonetkit.design.ip_addressing.ipv4.build_ipv4(
        anm, infrastructure=infrastructure)

def build_ipv6(anm):
    #TODO: check why ipv6 doesn't take infrastructure
    import autonetkit.design.ip_addressing.ipv6
    autonetkit.design.ip_addressing.ipv6.build_ipv6(
        anm)

#@call_log
