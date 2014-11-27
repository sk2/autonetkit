import autonetkit.ank as ank_utils
import autonetkit.log as log


def build_layer2(anm):
    build_layer2_base(anm)
    build_vlans(anm)
    build_layer2_conn(anm)

    check_layer2(anm)
    build_layer2_broadcast(anm)


def build_layer2_base(anm):
    g_l2 = anm.add_overlay('layer2')
    g_l1 = anm['layer1']

    g_l2.add_nodes_from(g_l1)
    g_l2.add_edges_from(g_l1.edges())
    # Don't aggregate managed switches
    for node in g_l2:
        if node['layer1'].collision_domain == True:
            node.broadcast_domain = True
            node.device_type = "broadcast_domain"

    try:
        from autonetkit_cisco import build_network as cisco_build_network
    except ImportError:
        pass
    else:
        cisco_build_network.post_layer2(anm)

    # Note: layer 2 base is much simpler since most is inherited from layer 1
    # cds


def build_layer2_conn(anm):
    g_l2 = anm['layer2']
    g_l2_conn = anm.add_overlay('layer2_conn')
    g_l2_conn.add_nodes_from(g_l2, retain="broadcast_domain")
    g_l2_conn.add_edges_from(g_l2.edges())

    broadcast_domains = g_l2_conn.nodes(broadcast_domain=True)
    exploded_edges = ank_utils.explode_nodes(g_l2_conn, broadcast_domains)

    # explode each seperately?
    for edge in exploded_edges:
        edge.multipoint = True
        edge.src_int.multipoint = True
        edge.dst_int.multipoint = True


def check_layer2(anm):
    """Sanity checks on topology"""
    from collections import defaultdict
    g_l2 = anm['layer2']

    # check for igp and ebgp on same switch
    for switch in sorted(g_l2.switches()):
        neigh_asns = defaultdict(int)
        for neigh in switch.neighbors():
            if neigh.asn is None:
                continue  # don't add if not set
            neigh_asns[neigh.asn] += 1

        # IGP if two or more neighbors share the same ASN
        is_igp = any(asns > 1 for asns in neigh_asns.values())
        # eBGP if more than one unique neigh ASN
        is_ebgp = len(neigh_asns.keys()) > 1
        if is_igp and is_ebgp:
            log.warning("Switch %s contains both IGP and eBGP neighbors",
                        switch)

    # check for multiple links from nodes to switch
    for switch in sorted(g_l2.switches()):
        for neighbor in sorted(switch.neighbors()):
            edges = g_l2.edges(switch, neighbor)
            if len(edges) > 1:
                # more than one edge between the (src, dst) pair -> parallel
                log.warning("Multiple edges (%s) between %s and device %s",
                            len(edges), switch, neighbor)


def build_layer2_broadcast(anm):
    g_l2 = anm['layer2']
    g_phy = anm['phy']
    g_graphics = anm['graphics']
    g_l2_bc = anm.add_overlay('layer2_bc')
    g_l2_bc.add_nodes_from(g_l2.l3devices())
    g_l2_bc.add_nodes_from(g_l2.switches())
    g_l2_bc.add_edges_from(g_l2.edges())

    # remove external connectors

    edges_to_split = [edge for edge in g_l2_bc.edges()
                      if edge.src.is_l3device() and edge.dst.is_l3device()]
    # TODO: debug the edges to split
    for edge in edges_to_split:
        edge.split = True  # mark as split for use in building nidb

    split_created_nodes = list(ank_utils.split(g_l2_bc, edges_to_split,
                                               retain=['split'],
                                               id_prepend='cd_'))

    # TODO: if parallel nodes, offset
    # TODO: remove graphics, assign directly
    if len(g_graphics):
        co_ords_overlay = g_graphics  # source from graphics overlay
    else:
        co_ords_overlay = g_phy  # source from phy overlay

    for node in split_created_nodes:
        node['graphics'].x = ank_utils.neigh_average(g_l2_bc, node, 'x',
                                                     co_ords_overlay) + 0.1

        # temporary fix for gh-90

        node['graphics'].y = ank_utils.neigh_average(g_l2_bc, node, 'y',
                                                     co_ords_overlay) + 0.1

        # temporary fix for gh-90

        asn = ank_utils.neigh_most_frequent(
            g_l2_bc, node, 'asn', g_phy)  # arbitrary choice
        node['graphics'].asn = asn
        node.asn = asn  # need to use asn in IP overlay for aggregating subnets

    # also allocate an ASN for virtual switches
    vswitches = [n for n in g_l2_bc.nodes()
                 if n['layer2'].device_type == "switch"
                 and n['layer2'].device_subtype == "virtual"]
    for node in vswitches:
        # TODO: refactor neigh_most_frequent to allow fallthrough attributes
        # asn = ank_utils.neigh_most_frequent(g_l2_bc, node, 'asn', g_l2)  #
        # arbitrary choice
        asns = [n['layer2'].asn for n in node.neighbors()]
        asns = [x for x in asns if x is not None]
        asn = ank_utils.most_frequent(asns)
        node.asn = asn  # need to use asn in IP overlay for aggregating subnets
        # also mark as broadcast domain

    from collections import defaultdict
    coincident_nodes = defaultdict(list)
    for node in split_created_nodes:
        coincident_nodes[(node['graphics'].x, node['graphics'].y)].append(node)

    coincident_nodes = {k: v for k, v in coincident_nodes.items()
                        if len(v) > 1}  # trim out single node co-ordinates
    import math
    for _, val in coincident_nodes.items():
        for index, item in enumerate(val):
            index = index + 1
            x_offset = 25 * math.floor(index / 2) * math.pow(-1, index)
            y_offset = -1 * 25 * math.floor(index / 2) * math.pow(-1, index)
            item['graphics'].x = item['graphics'].x + x_offset
            item['graphics'].y = item['graphics'].y + y_offset

    switch_nodes = g_l2_bc.switches()  # regenerate due to aggregated
    g_l2_bc.update(switch_nodes, broadcast_domain=True)

    # switches are part of collision domain
    g_l2_bc.update(split_created_nodes, broadcast_domain=True)

    # Assign collision domain to a host if all neighbours from same host

    for node in split_created_nodes:
        if ank_utils.neigh_equal(g_l2_bc, node, 'host', g_phy):
            node.host = ank_utils.neigh_attr(g_l2_bc, node, 'host',
                                             g_phy).next()  # first attribute

    # set collision domain IPs
    # TODO; work out why this throws a json exception
    #autonetkit.ank.set_node_default(g_l2_bc,  broadcast_domain=False)

    for node in g_l2_bc.nodes('broadcast_domain'):
        graphics_node = g_graphics.node(node)
        #graphics_node.device_type = 'broadcast_domain'
        if node.is_switch():
            # TODO: check not virtual
            node['phy'].broadcast_domain = True
        if not node.is_switch():
            # use node sorting, as accomodates for numeric/string names
            graphics_node.device_type = 'broadcast_domain'
            neighbors = sorted(neigh for neigh in node.neighbors())
            label = '_'.join(neigh.label for neigh in neighbors)
            cd_label = 'cd_%s' % label  # switches keep their names
            node.label = cd_label
            graphics_node.label = cd_label
            node.device_type = "broadcast_domain"
            node.label = node.id
            graphics_node.label = node.id

    for node in vswitches:
        node.broadcast_domain = True


def set_default_vlans(anm, default_vlan=2):
    #TODO: read default vlan from global input config (eg from .virl)
    # TODO: rename to "mark_defaults_vlan" or similar
    # checks all links to managed switches have vlans
    g_vtp = anm['vtp']
    g_l2 = anm['layer2']
    g_l1_conn = anm['layer1_conn']
    managed_switches = [n for n in g_vtp.switches()
                        if n.device_subtype == "managed"]

    no_vlan_ints = []
    for switch in managed_switches:
        for edge in switch.edges():
            neigh_int = edge.dst_int
            local_int = edge.src_int
            if neigh_int.node in managed_switches:
                neigh_int.trunk = True
                continue

            if neigh_int['input'].vlan is None:
                vlan = default_vlan
                no_vlan_ints.append(neigh_int)
            else:
                vlan = neigh_int['input'].vlan

            try:
                vlan = int(vlan)
            except TypeError:
                log.warning("Non-integer vlan %s for %s. Using default %s",
                    vlan, neigh_int, default_vlan)
                vlan = default_vlan

            neigh_int.vlan = vlan
            local_int.vlan = vlan

        for interface in switch:
            if interface.vlan and interface.trunk:
                log.warning("Interface %s set to trunk and vlan", interface)

    # map to layer 2 interfaces
    if len(no_vlan_ints):
        log.info("Setting default VLAN %s to interfaces connected to a managed "
           "switch with no VLAN: %s", default_vlan, no_vlan_ints)


def build_vlans(anm):
    import itertools
    from collections import defaultdict
    g_l2 = anm['layer2']
    g_l1_conn = anm['layer1_conn']
    g_phy = anm['phy']

    g_vtp = anm.add_overlay('vtp')
    # g_vlan = anm.add_overlay('vlan')
    managed_switches = [n for n in g_l2.switches()
                        if n.device_subtype == "managed"]

    g_vtp.add_nodes_from(g_l1_conn)
    g_vtp.add_edges_from(g_l1_conn.edges())

    # remove anything not a managed_switch or connected to a managed_switch
    keep = set()
    keep.update(managed_switches)
    for switch in managed_switches:
        keep.update(switch['vtp'].neighbors())

    remove = set(g_vtp) - keep
    g_vtp.remove_nodes_from(remove)

    edges_to_remove = [e for e in g_vtp.edges()
                       if not(e.src in managed_switches or e.dst in managed_switches)]
    g_vtp.remove_edges_from(edges_to_remove)

    # import ipdb
    # ipdb.set_trace()
    set_default_vlans(anm)

    # copy across vlans from input graph
    vswitch_id_counter = itertools.count(1)

    # TODO: aggregate managed switches

    bcs_to_trim = set()

    subs = ank_utils.connected_subgraphs(g_vtp, managed_switches)
    for sub in subs:
        # identify the VLANs on these switches
        vlans = defaultdict(list)
        sub_neigh_ints = set()
        for switch in sub:
            l2_switch = switch['layer2']
            bcs_to_trim.update(l2_switch.neighbors())
            neigh_ints = {iface for iface in switch.neighbor_interfaces()
                          if iface.node.is_l3device()
                          and iface.node not in sub}

            sub_neigh_ints.update(neigh_ints)

        for interface in sub_neigh_ints:
            # store keyed by vlan id
            vlan = interface['vtp'].vlan
            vlans[vlan].append(interface)

        log.debug("Vlans for sub %s are %s", sub, vlans)
        # create a virtual switch for each
        # TODO: naming: if this is the only pair then name after these, else
        # use the switch names too
        #vswitch_prefix = "_".join(str(sw) for sw in sub)
        vswitches = []  # store to connect trunks
        for vlan, interfaces in vlans.items():
            # create a virtual switch
            vswitch_id = "vswitch%s" % vswitch_id_counter.next()
            # vswitch = g_vlan.add_node(vswitch_id)
            vswitch = g_l2.add_node(vswitch_id)
            # TODO: check of switch or just broadcast_domain for higher layer
            # purposes
            vswitch.device_type = "switch"
            vswitch.device_subtype = "virtual"
            vswitches.append(vswitch)
            # TODO: layout based on midpoint of previous?
            # or if same number as real switches, use their co-ordinates?
            # and then check for coincident?
            vswitch.x = sum(
                i.node['phy'].x for i in interfaces) / len(interfaces) + 50
            vswitch.y = sum(
                i.node['phy'].y for i in interfaces) / len(interfaces) + 50
            vswitch.vlan = vlan

            vswitch['layer2'].broadcast_domain = True
            vswitch['layer2'].vlan = vlan

            # and connect from vswitch to the interfaces
            edges_to_add = [(vswitch, iface) for iface in interfaces]
            g_l2.add_edges_from(edges_to_add)

        # remove the physical switches
        g_l2.remove_nodes_from(bcs_to_trim)
        g_l2.remove_nodes_from(sub)
        # TODO: also remove any broadcast domains no longer connected

        # g_l2.remove_nodes_from(disconnected_bcs)

        # Note: we don't store the interface names as ciuld clobber
        # eg came from two physical switches, each on gige0
        # if need, work backwards from the router iface and its connectivity

        # and add the trunks
        # TODO: these need annotations!
        # create trunks
        edges_to_add = list(itertools.combinations(vswitches, 2))
        # TODO: ensure only once
        # TODO: filter so only one direction
        # g_vlan.add_edges_from(edges_to_add, trunk=True)
        g_vtp.add_edges_from(edges_to_add, trunk=True)
