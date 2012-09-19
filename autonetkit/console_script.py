from anm import AbstractNetworkModel
import ank
import itertools
from nidb import NIDB
import render
import random
import pprint
import os
import time
import compiler
import pkg_resources
import deploy
import measure
import math
import autonetkit.log as log
import autonetkit.plugins.ip as ip
import autonetkit.plugins.graph_product as graph_product
import autonetkit.plugins.route_reflectors as route_reflectors
import autonetkit.ank_json
import pika
import json
try:
    import cPickle as pickle
except ImportError:
    import pickle

#import pika.log
#pika.log.setup(pika.log.DEBUG, color=True)

def main():
    try:
        ank_version = pkg_resources.get_distribution("AutoNetkit").version
    except pkg_resources.DistributionNotFound:
        ank_version = "0.1"
    log.info("AutoNetkit %s" % ank_version)

    import optparse
    opt = optparse.OptionParser()
    opt.add_option('--file', '-f', default= None, help="Load topology from FILE")        
    opt.add_option('--monitor', '-m',  action="store_true", default= False, help="Monitor input file for changes")        
    opt.add_option('--debug',  action="store_true", default= False, help="Debug mode")        
    opt.add_option('--compile',  action="store_true", default= False, help="Compile")        
    opt.add_option('--deploy',  action="store_true", default= False, help="Deploy")        
    opt.add_option('--measure',  action="store_true", default= False, help="Measure")        
    opt.add_option('--webserver',  action="store_true", default= False, help="Webserver")        
    options, arguments = opt.parse_args()

    #import diff
    #pprint.pprint(diff.nidb_diff("versions/nidb"))

    input_filename = options.file
    if not options.file:
        input_filename = "ank.graphml"

    if options.debug:
        #TODO: fix this
        import logging
        logger = logging.getLogger("ANK")
        logger.setLevel(logging.DEBUG)

#TODO: put compile logic into a function that both compile and monitor call rather than duplicated code

    if options.compile:
        anm = build_network(input_filename)
        www_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='115.146.94.68'))
        www_channel = www_connection.channel()
        www_channel.exchange_declare(exchange='www',
                type='direct')
        anm.save()
        nidb = compile_network(anm)
        body = autonetkit.ank_json.dumps(anm, nidb)
        #fh = open("ank_vis/default.json", "w")
        #fh.write(body)
        #fh.close()
        import zlib
        body = zlib.compress(body, 9)
        www_channel.basic_publish(exchange='www',
                routing_key = "client",
                body= body)
        log.debug("Sent ANM to web server")
        nidb.save()
    else:
        anm = AbstractNetworkModel()
        anm.restore_latest()
        nidb = NIDB()
        nidb.restore_latest()
        render.remove_dirs(["rendered/nectar1/nklab/"])
        render.render(nidb)

    if options.deploy:
        deploy_network(nidb)
    if options.measure:
        measure_network(nidb)

    if options.webserver:
        log.info("Webserver not yet supported, run as seperate module")
#TODO: run as seperate thread
        #import autonetkit.webserver
        #autonetkit.webserver.main()
        #log.info("Started webserver")

    if options.monitor:
        try:
            log.info("Monitoring for updates...")
            prev_timestamp = 0
            while True:
                time.sleep(0.1)
                latest_timestamp = os.stat(input_filename).st_mtime
                if latest_timestamp > prev_timestamp:
                    prev_timestamp = latest_timestamp
                    try:
                        log.info("Input graph updated, recompiling network")
                        if options.compile:
                            anm = build_network(input_filename)
                            anm.save()
                            nidb = compile_network(anm)
                            body = autonetkit.ank_json.dumps(anm)
                            import zlib
                            body = zlib.compress(body, 9)
                            www_channel.basic_publish(exchange='www',
                                    routing_key = "client",
                                    body= body)
                            nidb.save()
                            render.remove_dirs(["rendered/nectar1/nklab/"])
                            render.render(nidb)

                        else:
                            anm = AbstractNetworkModel()
                            anm.restore_latest()
                            nidb = NIDB()
                            nidb.restore_latest()

                        if options.deploy:
                            deploy_network(nidb)
                        if options.measure:
                            measure_network(nidb)

                        log.info("Monitoring for updates...")
                    except Exception, e:
                        # TODO: remove this, add proper warning
                        log.warning("Unable to build network: %s" % e)
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
    G_phy.add_nodes_from(G_in, retain=['label', 'device_type', 'device_subtype', 'asn', 'platform', 'host', 'syntax'])
    if G_in.data.Creator == "Topology Zoo Toolset":
        ank.copy_attr_from(G_in, G_phy, "Network") # Copy Network from Zoo
# build physical graph
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
           link.cost = 8
           link.area = 0

    non_same_asn_edges = [link for link in G_ospf.edges() if link.src.asn != link.dst.asn]
    G_ospf.remove_edges_from(non_same_asn_edges)

def build_network(input_filename):
    #TODO: move this out of main console wrapper
    anm = AbstractNetworkModel()
    input_graph = ank.load_graphml(input_filename)

    G_in = anm.add_overlay("input", input_graph)
    ank.set_node_default(G_in, G_in, platform="netkit")
    ank.set_node_default(G_in, G_in, host="nectar1")

    graph_product.expand(G_in) # apply graph products if relevant
    
    if len(ank.unique_attr(G_in, "asn")) > 1:
        # Multiple ASNs set, use label format device.asn 
        anm.set_node_label(".",  ['label', 'pop', 'asn'])

# set syntax for routers according to platform
    G_in.update(G_in.nodes("is_router", platform = "junosphere"), syntax="junos")
    G_in.update(G_in.nodes("is_router", platform = "dynagen"), syntax="ios")
    G_in.update(G_in.nodes("is_router", platform = "netkit"), syntax="quagga")

    G_graphics = anm.add_overlay("graphics") # plotting data
    G_graphics.add_nodes_from(G_in, retain=['x', 'y', 'device_type', 'device_subtype', 'pop', 'asn'])

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
    nidb.add_nodes_from(G_phy, retain=['label', 'host', 'platform', 'Network'])

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
        node.graphics.device_subtype = graphics_node.device_subtype
        node.device_type = graphics_node.device_type
        node.device_subtype = graphics_node.device_subtype

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

def deploy_network(nidb):
    log.info("Deploying network")
    tar_file = deploy.package("rendered/nectar1/nklab/", "nklab")
    server = "trc1.trc.adelaide.edu.au"
    username = "sknight"

    server = "115.146.93.255" # 16 core
    server = "115.146.94.68" # 8 core
    username = "ubuntu"
    key_filename = "/Users/sk2/.ssh/sk.pem"
    
    deploy.transfer(server, username, tar_file, tar_file, key_filename)
    cd_dir = "rendered/nectar1/nklab/"
    deploy.extract(server, username, tar_file, cd_dir, timeout = 60, key_filename= key_filename)

def measure_network(nidb):
    log.info("Measuring network")
    remote_hosts = [node.tap.ip for node in nidb.nodes("is_router") ]
    dest_node = random.choice([n for n in nidb.nodes("is_l3device")])
    log.info("Tracing to randomly selected node: %s" % dest_node)
# choose random interface on this node
    dest_ip = dest_node.interfaces[0].ip_address

    command = "traceroute -n -a -U -w 0.5 %s" % dest_ip 
    # abort after 10 fails, proceed on any success, 0.1 second timeout (quite aggressive)
    #command = 'vtysh -c "show ip route"'
    measure.send(nidb, "nectar1", command, remote_hosts)
    remote_hosts = [node.tap.ip for node in nidb.nodes("is_router") if node.bgp.ebgp_neighbors]
    command = "cat /var/log/zebra/bgpd.log"
    #measure.send(nidb, "nectar1", command, remote_hosts)
    #command = 'vtysh -c "show ip bgp summary"'
    #measure.send(nidb, "nectar1", command, remote_hosts)
    #command = 'vtysh -c "show ip bgp summary"'
    #measure.send(nidb, "nectar1", command, remote_hosts)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
