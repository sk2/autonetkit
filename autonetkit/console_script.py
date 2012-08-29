from anm import AbstractNetworkModel
import ank
import itertools
from nidb import NIDB
import render
import time
import compiler
import pkg_resources
import change_monitor
import deploy
import math
import autonetkit.log as log
import autonetkit.plugins.ip as ip
import autonetkit.plugins.route_reflectors as route_reflectors

def main():
    ank_version = pkg_resources.get_distribution("AutoNetkit").version
    log.info("AutoNetkit %s" % ank_version)

    import optparse
    opt = optparse.OptionParser()
    opt.add_option('--file', '-f', default= None, help="Load topology from FILE")        
    opt.add_option('--monitor', '-m',  action="store_true", default= False, help="Monitor input file for changes")        
    options, arguments = opt.parse_args()

    input_filename = options.file
    if not options.file:
        input_filename = "ank.graphml"

    anm = build_network(input_filename)
    anm.save()
    nidb = compile_network(anm)
    render.render(nidb)
    #deploy_network()

    if options.monitor:
        try:
            log.info("Monitoring for updates...")
            while True:
                time.sleep(0.2)
                if change_monitor.check_for_change(input_filename, anm):
                    try:
                        log.info("Input graph updated, recompiling network")
                        anm = build_network(input_filename)
                        anm.save()
                        nidb = compile_network(anm)
                        render.render(nidb)
                        log.info("Monitoring for updates...")
                    except:
                        # TODO: remove this, add proper warning
                        log.warn("Unable to build network")
                        pass
        except KeyboardInterrupt:
            log.info("Exiting")

def build_bgp(anm):
    # eBGP
    G_phy = anm['phy']
    G_in = anm['input']
    G_bgp = anm.add_overlay("bgp", directed = True)
    G_bgp.add_nodes_from(G_in.nodes("is_router"))
    ebgp_edges = [edge for edge in G_in.edges() if not edge.attr_equal("asn")]
    G_bgp.add_edges_from(ebgp_edges, bidirectional = True, type = 'ebgp')

# now iBGP
    if len(G_phy) < 500:
# full mesh
        for asn, devices in G_phy.groupby("asn").items():
            routers = [d for d in devices if d.is_router]
            ibgp_edges = [ (s, t) for s in routers for t in routers if s!=t]
            G_bgp.add_edges_from(ibgp_edges, type = 'ibgp')
    else:
        route_reflectors.allocate(G_phy, G_bgp)

#TODO: probably want to use l3 connectivity graph for allocating route reflectors

    ebgp_nodes = [d for d in G_bgp if any(edge.type == 'ebgp' for edge in d.edges())]
    G_bgp.update(ebgp_nodes, ebgp=True)

def build_ip(anm):
    G_ip = anm.add_overlay("ip")
    G_in = anm['input']
    G_graphics = anm['graphics']
    G_phy = anm['phy']

    G_ip.add_nodes_from(G_in)
    G_ip.add_edges_from(G_in.edges(type="physical"))

    ank.aggregate_nodes(G_ip, G_ip.nodes("is_switch"), retain = "edge_id")
#TODO: add function to update edge properties: can overload node update?

#TODO: abstract this better
    edges_to_split = [edge for edge in G_ip.edges() if edge.attr_both("is_l3device")]
    split_created_nodes = list(ank.split(G_ip, edges_to_split, retain='edge_id'))
    for node in split_created_nodes:
        node.overlay.graphics.x = ank.neigh_average(G_ip, node, "x", G_graphics)
        node.overlay.graphics.y = ank.neigh_average(G_ip, node, "y", G_graphics)
        node.overlay.graphics.asn = math.floor(ank.neigh_average(G_ip, node, "asn", G_phy)) # arbitrary choice

    switch_nodes = G_ip.nodes("is_switch")# regenerate due to aggregated
    G_ip.update(switch_nodes, collision_domain=True) # switches are part of collision domain
    G_ip.update(split_created_nodes, collision_domain=True)
# Assign collision domain to a host if all neighbours from same host
    for node in split_created_nodes:
        if ank.neigh_equal(G_ip, node, "host", G_phy):
            node.host = ank.neigh_attr(G_ip, node, "host", G_phy).next() # first attribute

# set collision domain IPs
    collision_domain_id = (i for i in itertools.count(0))
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
# build physical graph
    G_phy.add_nodes_from(G_in, retain=['label', 'device_type', 'asn', 'platform', 'host', 'syntax'])
    G_phy.add_edges_from([edge for edge in G_in.edges() if edge.type == "physical"])

def build_ospf(anm):
    G_in = anm['input']
    G_ospf = anm.add_overlay("ospf")
    G_ospf.add_nodes_from(G_in.nodes("is_router"), retain=['asn'])
    G_ospf.add_nodes_from(G_in.nodes("is_switch"), retain=['asn'])
    G_ospf.add_edges_from(G_in.edges(), retain = ['edge_id', 'ospf_cost'])
#TODO: trim out non same asn edges
    ank.aggregate_nodes(G_ospf, G_ospf.nodes("is_switch"), retain = "edge_id")
    ank.explode_nodes(G_ospf, G_ospf.nodes("is_switch"))
    for link in G_ospf.edges():
           link.cost = 1
           link.area = 0

    non_same_asn_edges = [link for link in G_ospf.edges() if link.src.asn != link.dst.asn]
    G_ospf.remove_edges_from(non_same_asn_edges)

def build_network(input_filename):
    anm = AbstractNetworkModel()
    input_graph = ank.load_graphml(input_filename)

    G_in = anm.add_overlay("input", input_graph)
    ank.set_node_default(G_in, G_in, platform="netkit")
    ank.set_node_default(G_in, G_in, host="nectar1")
    
    if len(ank.unique_attr(G_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn 
        anm.set_node_label(".as",  ['label', 'asn'])

# set syntax for routers according to platform
    G_in.update(G_in.nodes("is_router", platform = "junosphere"), syntax="junos")
    G_in.update(G_in.nodes("is_router", platform = "dynagen"), syntax="ios")
    G_in.update(G_in.nodes("is_router", platform = "netkit"), syntax="quagga")

    G_graphics = anm.add_overlay("graphics") # plotting data
    G_graphics.add_nodes_from(G_in, retain=['x', 'y', 'device_type', 'asn'])

    build_phy(anm)
    build_ip(anm)
    build_ospf(anm)
    build_bgp(anm)

    return anm


def compile_network(anm):
    nidb = NIDB() 
    G_phy = anm.overlay.phy
    G_ip = anm.overlay.ip
    G_graphics = anm.overlay.graphics
#TODO: build this on a platform by platform basis
    nidb.add_nodes_from(G_phy, retain=['label', 'host', 'platform'])

    nidb.add_nodes_from(G_ip.nodes("collision_domain"), retain=['label', 'host'], collision_domain = True)
# add edges to switches
    edges_to_add = [edge for edge in G_phy.edges() if edge.src.is_switch or edge.dst.is_switch]
    edges_to_add += [edge for edge in G_ip.edges() if edge.src.collision_domain or edge.dst.collision_domain]
    nidb.add_edges_from(edges_to_add, retain='edge_id')

#TODO: boundaries is still a work in progress...
    for node in nidb:
        graphics_node = G_graphics.node(node)
        node.graphics.x = graphics_node.x
        node.graphics.y = graphics_node.y
        node.graphics.device_type = graphics_node.device_type
        node.device_type = graphics_node.device_type

    host = "nectar1"
    #junosphere_compiler = compiler.JunosphereCompiler(nidb, anm, host)
    #junosphere_compiler.compile()
    netkit_compiler = compiler.NetkitCompiler(nidb, anm, host)
    netkit_compiler.compile()
    #dynagen_compiler = compiler.DynagenCompiler(nidb, anm, host)
    #dynagen_compiler.compile()

    #cisco_compiler = compiler.CiscoCompiler(nidb, anm, host)
    #cisco_compiler.compile()

    return nidb

def deploy_network():
    log.info("Deploying network")
    tar_file = deploy.package("rendered/nectar1/netkit/", "netkit")
    server = "trc1.trc.adelaide.edu.au"
    deploy.transfer(server, "sknight", tar_file, tar_file)
    print "server", server
    cd_dir = "rendered/nectar1/netkit/"
    deploy.extract(server, tar_file, cd_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
