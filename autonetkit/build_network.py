import autonetkit
import autonetkit.anm
import autonetkit.ank as ank
import itertools
import autonetkit.ank_pika
import autonetkit.config
settings = autonetkit.config.settings
import autonetkit.log as log
import autonetkit.load.graphml as graphml
import autonetkit.exception
import networkx as nx
import os


__all__ = ['build']

rabbitmq_server = settings['Rabbitmq']['server']
pika_channel = autonetkit.ank_pika.AnkPika(rabbitmq_server)

#TODO: seperate out load and build - build should take a ready made nx graph and work from there.... load should do file handling error checking etc
# Also makes automated testing easier!

def build(input_graph_string, timestamp):
    #TODO: move this out of main console wrapper
    anm = autonetkit.anm.AbstractNetworkModel()
    
    try:
        input_graph = graphml.load_graphml(input_graph_string)
    except autonetkit.exception.AnkIncorrectFileFormat:
# try a different reader
        try:
            import autonetkit.load.worm as worm
        except ImportError:
            return # module not present (development module)
        input_graph = worm.load(input_graph_string)
# add local deployment host
        settings['General']['deploy'] = True
        settings['Deploy Hosts']['internal'] = {
                'cisco': {
                    'deploy': True,
                    },
                }

    #TODO: make this more explicit than overloading add_overlay - make it load_graph or something similar
    input_undirected = nx.Graph(input_graph)
    for node in input_graph:
        #del input_graph.node[node]['router config']
        #del input_graph.node[node]['device_subtype']
        pass
    #nx.write_graphml(input_graph, "output.graphml")
    G_in = anm.add_overlay("input", input_undirected)
    #G_in_directed = anm.add_overlay("input_directed", input_graph, directed = True)

    import autonetkit.plugins.graph_product as graph_product
    graph_product.expand(G_in) # apply graph products if relevant
    
    if len(ank.unique_attr(G_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn 
        anm.set_node_label(".",  ['label', 'pop', 'asn'])

#TODO: remove, used for demo on nectar
    #for node in G_in:
        #node.platform = "netkit"
        #node.host = "nectar1"
    #G_in.data.igp = "ospf"

# set syntax for routers according to platform
#TODO: make these defaults
    G_in.update(G_in.nodes("is_router", platform = "junosphere"), syntax="junos")
    G_in.update(G_in.nodes("is_router", platform = "dynagen"), syntax="ios")
    G_in.update(G_in.nodes("is_router", platform = "netkit"), syntax="quagga")
    #G_in.update(G_in.nodes("is_router", platform = "cisco"), syntax="ios2")

    G_graphics = anm.add_overlay("graphics") # plotting data
    G_graphics.add_nodes_from(G_in, retain=['x', 'y', 'device_type', 'device_subtype', 'pop', 'asn'])

    build_phy(anm)
    #update_pika(anm)
    #build_conn(anm)
    build_ip(anm)
    
    igp = G_in.data.igp or "ospf" #TODO: make default template driven
#TODO: make the global igp be set on each node - this way can also support different IGPs per router

# Add overlays even if not used: simplifies compiler where can check for presence in overlay (if blank not present, don't configure ospf etc)
    anm.add_overlay("ospf")
    anm.add_overlay("isis")
    
    if igp == "ospf":
        build_ospf(anm)
    if igp == "isis":
        build_isis(anm)
    build_bgp(anm)
    return anm


def boundary_nodes(G, nodes):
    #TODO: move to utils
    """ returns nodes at boundary of G
    TODO: check works for both directed and undirected graphs
    based on edge_boundary from networkx """
    import autonetkit.ank as ank_utils
    graph = ank_utils.unwrap_graph(G)
    #print graph_phy.nodes()
    nodes = list(nodes)
    nbunch = list(ank_utils.unwrap_nodes(nodes))
    # find boundary
    b_edges = nx.edge_boundary(graph, nbunch) # boundary edges
    internal_nodes = [s for (s, t) in b_edges]
    assert(all(n in nbunch for n in internal_nodes)) # check internal 

    return ank_utils.wrap_nodes(G, internal_nodes)
#TODO: catch AssertionError, handle through logging/warning
# Node boundary returns external nodes connected to nodes in nbunch
# for now use edge boundary, and find any node in nbunch connected to these edges


def build_bgp(anm):
    # eBGP
    G_phy = anm['phy']
    G_in = anm['input']
    G_bgp = anm.add_overlay("bgp", directed = True)
    G_bgp.add_nodes_from(G_in.nodes("is_router"))
    ebgp_edges = [edge for edge in G_in.edges() if not edge.attr_equal("asn")]
    G_bgp.add_edges_from(ebgp_edges, bidirectional = True, type = 'ebgp')

# now iBGP
#TODO: add flag for three iBGP types: full-mesh, algorithmic, custom
    if False:
        #TODO: need to allow manually set ibgp_level2 and ibgp_level1 groups, fallback is region/asn
        ank.copy_attr_from(G_in, G_phy, "region") 
        for asn, devices in G_phy.groupby("asn").items():
            as_graph = G_phy.subgraph(devices)
# want to group by asn, then group by region
            for region, region_devices in as_graph.groupby("region").items():
                b_nodes = boundary_nodes(as_graph, region_devices)
                route_reflectors = list(b_nodes) #TODO: may want to limit number if boundary nodes to set as route reflector
# eg could sort, choose most connected, most central, etc
                for n in route_reflectors:
                    log.debug("Setting rr for %s" % n)
                    G_bgp.node(n).route_reflector = True

                rr_clients = set(region_devices) - set(route_reflectors)

                # now connect region devices
                # rr to rr (over)
                over_links = [(rr1, rr2) for (rr1, rr2) in itertools.product(route_reflectors, route_reflectors)]
                G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')
                

                # rr to rrc (down)
                down_links = [(rr, client) for (rr, client) in itertools.product(route_reflectors, rr_clients)]
                G_bgp.add_edges_from(down_links, type = 'ibgp', direction = 'down')

                # rrc to rr (up)
                up_links = [(client, rr) for (client, rr) in itertools.product(rr_clients, route_reflectors)]
                G_bgp.add_edges_from(up_links, type = 'ibgp', direction = 'up')

            # and connect all Route-reflectors in the same AS
            asn_rrs = list(G_bgp.nodes(asn=asn, route_reflector = True))
            over_links = [(rr1, rr2) for (rr1, rr2) in itertools.product(asn_rrs, asn_rrs)]
            G_bgp.add_edges_from(over_links, type = 'ibgp', direction = 'over')

    if True:
        ank.copy_attr_from(G_in, G_bgp, "ibgp_level") 
        ank.copy_attr_from(G_in, G_bgp, "ibgp_l2_cluster") 
        ank.copy_attr_from(G_in, G_bgp, "ibgp_l3_cluster") 
        for node in G_bgp:
            #set defaults
#TODO: map "None" string to None for attributes from Graphml
            if not node.ibgp_level or node.ibgp_level == "None":
                node.ibgp_level = 1

            node.ibgp_level = int(node.ibgp_level) # ensure is numeric

            if not node.ibgp_l2_cluster or node.ibgp_l2_cluster == "None":
                pass
                node.ibgp_l2_cluster = node.region # ibgp_l2_cluster defaults to region
                #TODO: check region exists
            if not node.ibgp_l3_cluster or node.ibgp_l3_cluster == "None":
                node.ibgp_l3_cluster = node.asn # ibgp_l3_cluster defaults to ASN

        for asn, devices in G_phy.groupby("asn").items():
            as_graph = G_phy.subgraph(devices)
            routers = list(n for n in as_graph if n.is_router)
#TODO: catch integer cast exception
            ibgp_levels = set(int(G_bgp.node(r).ibgp_level) for r in routers)
            max_level = max(ibgp_levels)
            all_pairs = [ (G_bgp.node(s), G_bgp.node(t)) for s in routers for t in routers if s != t]
            if max_level == 3:
                l1_l2_up_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == 1 and t.ibgp_level == 2
                        and s.ibgp_l2_cluster == t.ibgp_l2_cluster]
                l1_l2_down_links = [ (t, s) for (s, t) in l1_l2_up_links] # the reverse
                G_bgp.add_edges_from(l1_l2_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l1_l2_down_links, type = 'ibgp', direction = 'down')


                l2_peer_links = [ (s, t) for (s, t) in all_pairs 
                        if s.ibgp_level == t.ibgp_level == 2 and s.ibgp_l2_cluster == t.ibgp_l2_cluster ]
                G_bgp.add_edges_from(l2_peer_links, type = 'ibgp', direction = 'over')


                l2_l3_up_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == 2 and t.ibgp_level == 3
                        and s.ibgp_l3_cluster == t.ibgp_l3_cluster]
                l2_l3_down_links = [ (t, s) for (s, t) in l2_l3_up_links] # the reverse
                G_bgp.add_edges_from(l2_l3_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l2_l3_down_links, type = 'ibgp', direction = 'down')

                l3_peer_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == t.ibgp_level == 3]
                G_bgp.add_edges_from(l3_peer_links, type = 'ibgp', direction = 'over')

            if max_level == 2:
                l1_l2_up_links = [ (s, t) for (s, t) in all_pairs if s.ibgp_level == 1 and t.ibgp_level == 2
                        and s.ibgp_l3_cluster == t.ibgp_l2_cluster]
                l1_l2_down_links = [ (t, s) for (s, t) in l1_l2_up_links] # the reverse
                G_bgp.add_edges_from(l1_l2_up_links, type = 'ibgp', direction = 'up')
                G_bgp.add_edges_from(l1_l2_down_links, type = 'ibgp', direction = 'down')

                l2_peer_links = [ (s, t) for (s, t) in all_pairs 
                        if s.ibgp_level == t.ibgp_level == 2 and s.ibgp_l3_cluster == t.ibgp_l3_cluster ]
                G_bgp.add_edges_from(l2_peer_links, type = 'ibgp', direction = 'over')

    elif len(G_phy) < 5:
# full mesh
        for asn, devices in G_phy.groupby("asn").items():
            routers = [d for d in devices if d.is_router]
            ibgp_edges = [ (s, t) for s in routers for t in routers if s!=t]
            G_bgp.add_edges_from(ibgp_edges, type = 'ibgp')
    else:
        import autonetkit.plugins.route_reflectors as route_reflectors
        route_reflectors.allocate(G_phy, G_bgp)

#TODO: probably want to use l3 connectivity graph for allocating route reflectors

    ebgp_nodes = [d for d in G_bgp if any(edge.type == 'ebgp' for edge in d.edges())]
    G_bgp.update(ebgp_nodes, ebgp=True)

def build_ip(anm):
    import autonetkit.plugins.ip as ip
    G_ip = anm.add_overlay("ip")
    G_in = anm['input']
    G_graphics = anm['graphics']
    G_phy = anm['phy']

    G_ip.add_nodes_from(G_in)
    G_ip.add_edges_from(G_in.edges(type="physical"))

    ank.aggregate_nodes(G_ip, G_ip.nodes("is_switch"), retain = "edge_id")
#TODO: add function to update edge properties: can overload node update?

    edges_to_split = [edge for edge in G_ip.edges() if edge.attr_both("is_l3device")]
    split_created_nodes = list(ank.split(G_ip, edges_to_split, retain='edge_id'))
    for node in split_created_nodes:
        node['graphics'].x = ank.neigh_average(G_ip, node, "x", G_graphics)
        node['graphics'].y = ank.neigh_average(G_ip, node, "y", G_graphics)
        node['graphics'].asn = ank.neigh_most_frequent(G_ip, node, "asn", G_phy) # arbitrary choice
#TODO: could choose largest ASN if tie break
#TODO: see if need G_phy - should auto fall through to phy for ASN

    switch_nodes = G_ip.nodes("is_switch")# regenerate due to aggregated
    G_ip.update(switch_nodes, collision_domain=True) # switches are part of collision domain
    G_ip.update(split_created_nodes, collision_domain=True)
# Assign collision domain to a host if all neighbours from same host
    for node in split_created_nodes:
        if ank.neigh_equal(G_ip, node, "host", G_phy):
            node.host = ank.neigh_attr(G_ip, node, "host", G_phy).next() # first attribute

# set collision domain IPs
#TODO: trim next line
    collision_domain_id = itertools.count(0)
    for node in G_ip.nodes("collision_domain"):
        graphics_node = G_graphics.node(node)
        graphics_node.device_type = "collision_domain"
        cd_id = collision_domain_id.next()
        node.cd_id = cd_id
#TODO: Use this label
        if not node.is_switch:
            label = "_".join(sorted(ank.neigh_attr(G_ip, node, "label", G_phy)))
            cd_label = "cd_%s" % label # switches keep their names
            node.label = cd_label 
            node.cd_id = cd_label
            graphics_node.label = cd_label

    ip.allocate_ips(G_ip)
    ank.save(G_ip)

def build_phy(anm):
    G_in = anm['input']
    G_phy = anm['phy']
    G_phy.add_nodes_from(G_in, retain=['label', 'update', 'device_type', 'device_subtype', 'asn', 'platform', 'host', 'syntax'])
    if G_in.data.Creator == "Topology Zoo Toolset":
        ank.copy_attr_from(G_in, G_phy, "Network") #TODO: move this into graphml (and later gml) reader

    G_phy.add_edges_from(G_in.edges(type="physical"))


def build_conn(anm):
    G_in = anm['input']
    G_phy = anm['phy']
    G_conn = anm.add_overlay("conn", directed = True)
    G_conn.add_nodes_from(G_in, retain=['label'])
    G_conn.add_edges_from(G_in.edges(type="physical"))

    #if G_in.data.Creator == "Maestro":
        #ank.copy_edge_attr_from(G_in, G_conn, "index")

    return

    import autonetkit.allocate_hardware
    autonetkit.allocate_hardware.allocate(anm)

    G_graphics = anm['graphics']

    new_nodes = set(G_conn) - set(G_phy)
    #G_graphics.add_nodes_from(new_nodes, retain = ['x', 'y', 'asn', "device_type", "device_subtype"])
    for node in new_nodes:
        G_graphics.add_node(node, retain = ['x', 'y', 'asn', "device_type", "device_subtype"])
        #print node['graphics'].dump()

#TODO: Add a function to auto-update graphics, if any node present in overlay but not in graphics then add with sensible defaults

def build_ospf(anm):
    """
    Build OSPF graph.
    
    Allowable area combinations:
    0 -> 0
    0 -> x (x!= 0)
    x -> 0 (x!= 0)
    x -> x (x != 0)

    Not-allowed:
    x -> x (x != y != 0)
    """
    G_in = anm['input']
    G_ospf = anm.add_overlay("ospf")
    G_ospf.add_nodes_from(G_in.nodes("is_router"), retain=['asn'])
    G_ospf.add_nodes_from(G_in.nodes("is_switch"), retain=['asn'])
    G_ospf.add_edges_from(G_in.edges(), retain = ['edge_id'])

    ank.copy_attr_from(G_in, G_ospf, "ospf_area", dst_attr = "area") #TODO: move this into graphml (and later gml) reader

    ank.aggregate_nodes(G_ospf, G_ospf.nodes("is_switch"), retain = "edge_id")
    ank.explode_nodes(G_ospf, G_ospf.nodes("is_switch"), retain= "edge_id")

    G_ospf.remove_edges_from([link for link in G_ospf.edges() if link.src.asn != link.dst.asn]) # remove inter-AS links

    for router in G_ospf:
        if not router.area or router.area == "None":
            #TODO: tidy up this default of None being a string
            router.area = 0

        router.area = int(router.area) #TODO: use dst type in copy_attr_from

 
    for router in G_ospf:
# and set area on interface
        for edge in router.edges():
            if edge.area:
                continue # already allocated (from other "direction", as undirected)
            if router.area == edge.dst.area:
                edge.area = router.area # intra-area
            else:
                if router.area == 0 or edge.dst.area == 0:
# backbone to other area
                    if router.area == 0:
                        edge.area = edge.dst.area # router in backbone, use other area
                    else:
                        edge.area = router.area # router not in backbone, use its area


    for router in G_ospf:
        areas = set(edge.area for edge in router.edges())
        if len(areas) == 0:
            router.type = "backbone" # no ospf edges (such as single node in AS)
        elif len(areas) == 1:
            # single area: either backbone (all 0) or internal (all nonzero)
            if 0 in areas:
                router.type = "backbone"
            else:
                router.type = "internal"

        else:
            # multiple areas
            if 0 in areas:
                router.type = "backbone ABR"
            else:
                log.warning("%s spans multiple areas but is not a member of area 0" % router)
                router.type = "INVALID"

#TODO: do we want to allocate non-symmetric OSPF costs? do we need a directed OSPF graph?
# (note this will all change once have proper interface nodes)

    for link in G_ospf.edges():
        link.cost = 1

def ip_to_net_ent_title_ios(ip):
    """ Converts an IP address into an OSI Network Entity Title
    suitable for use in IS-IS on IOS.

    >>> ip_to_net_ent_title_ios(IPAddress("192.168.19.1"))
    '49.1921.6801.9001.00'
    """
    try:
        ip_words = ip.words
    except AttributeError:
        import netaddr # try to cast to IP Address
        ip = netaddr.IPAddress(ip)
        ip_words = ip.words

    log.debug("Converting IP to OSI ENT format")
    area_id = "49"
    ip_octets = "".join("%03d" % int(octet) for octet in ip_words) # single string, padded if needed
    return ".".join([area_id, ip_octets[0:4], ip_octets[4:8], ip_octets[8:12], "00"])

def build_isis(anm):
    G_in = anm['input']
    G_ip = anm['ip']
    G_isis = anm.add_overlay("isis")
    #G_isis.add_nodes_from(G_in.nodes("is_router", igp = "isis"), retain=['asn'])
#TODO: filter only igp=isis nodes, set the igp as a default in build_network
    G_isis.add_nodes_from(G_in.nodes("is_router"), retain=['asn'])
    G_isis.add_nodes_from(G_in.nodes("is_switch"), retain=['asn'])
    G_isis.add_edges_from(G_in.edges(), retain = ['edge_id'])
# Merge and explode switches
    ank.aggregate_nodes(G_isis, G_isis.nodes("is_switch"), retain = "edge_id")
    ank.explode_nodes(G_isis, G_isis.nodes("is_switch"), retain = "edge_id")

    G_isis.remove_edges_from([link for link in G_isis.edges() if link.src.asn != link.dst.asn])

    for node in G_isis:
        ip_node = G_ip.node(node)
        node.net = ip_to_net_ent_title_ios(ip_node.loopback)
        node.process_id = 1 # default

    for link in G_isis.edges():
        link.metric = 1 # default

def update_pika(anm):
    log.debug("Sending anm to pika")
    body = autonetkit.ank_json.dumps(anm, None)
    pika_channel.publish_compressed("www", "client", body)
