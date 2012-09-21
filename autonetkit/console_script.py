from nidb import NIDB
import render
import random
import pprint
import traceback
import os
import time
import compiler
import pkg_resources
import deploy
import measure
import autonetkit.log as log
import autonetkit.ank_pika as ank_pika
import autonetkit.config as config

class FileMonitor(object):
    """Lightweight polling-based monitoring to see if file has changed"""
    def __init__(self, filename):
        self.filename = filename
        self.last_timestamp = os.stat(filename).st_mtime

    def has_changed(self):
        """Returns if file has changed since last called"""
        timestamp = os.stat(self.filename).st_mtime
        if timestamp > self.last_timestamp:
            self.last_timestamp = timestamp
            return True
        return False

def manage_network(input_filename, build_options, reload_build=False):
    import build_network
    if reload_build:
        build_network = reload(build_network)
    settings = config.settings

    if build_options['compile']:
        anm = build_network.build(input_filename)
        rabbitmq_server = settings['Rabbitmq']['server']
        pika_channel = ank_pika.AnkPika(rabbitmq_server)

        anm.save()
        nidb = compile_network(anm)
        import autonetkit.ank_json
        body = autonetkit.ank_json.dumps(anm, nidb)
        pika_channel.publish_compressed("www", "client", body)
        log.debug("Sent ANM to web server")
        nidb.save()
        render.remove_dirs(["rendered/nectar1/nklab/"])
        render.render(nidb)

    else:
        import autonetkit.anm
        anm = autonetkit.anm.AbstractNetworkModel()
        anm.restore_latest()
        nidb = NIDB()
        nidb.restore_latest()

    if build_options['deploy']:
        deploy_network(nidb)
    if build_options['measure']:
        measure_network(nidb)

def parse_options():
    import optparse
    opt = optparse.OptionParser()
    opt.add_option('--file', '-f', default= None, help="Load topology from FILE")        
    opt.add_option('--monitor', '-m',  action="store_true", default= False, help="Monitor input file for changes")        
    opt.add_option('--debug',  action="store_true", default= False, help="Debug mode")        
    opt.add_option('--compile',  action="store_true", default= False, help="Compile")        
    opt.add_option('--render',  action="store_true", default= False, help="Compile")        
    opt.add_option('--deploy',  action="store_true", default= False, help="Deploy")        
    opt.add_option('--measure',  action="store_true", default= False, help="Measure")        
    opt.add_option('--webserver',  action="store_true", default= False, help="Webserver")        
    options, arguments = opt.parse_args()
    return options, arguments

def main():
    settings = config.settings
    try:
        ank_version = pkg_resources.get_distribution("AutoNetkit").version
    except pkg_resources.DistributionNotFound:
        ank_version = "0.1"
    log.info("AutoNetkit %s" % ank_version)

    options, arguments = parse_options()

    input_filename = options.file
    if not options.file:
        input_filename = "ank.graphml"

    if options.debug:
        #TODO: fix this
        import logging
        logger = logging.getLogger("ANK")
        logger.setLevel(logging.DEBUG)

    build_options = {
            'compile':  options.compile or settings['General']['compile'],
            'deploy': options.deploy or settings['General']['deploy'],
            'measure': options.measure or settings['General']['measure'],
            'monitor': options.monitor or settings['General']['monitor'],
            }

    if options.webserver:
        log.info("Webserver not yet supported, run as seperate module")

    manage_network(input_filename, build_options)
    if build_options['monitor']:
        try:
            log.info("Monitoring for updates...")
            input_filemonitor = FileMonitor(input_filename)
            build_filemonitor = FileMonitor("autonetkit/build_network.py")
            while True:
                time.sleep(0.1)
                rebuild = False
                reload_build = False
                if input_filemonitor.has_changed():
                    rebuild = True
                if build_filemonitor.has_changed():
                    reload_build = True
                    rebuild = True

                if rebuild:
                    try:
                        log.info("Input graph updated, recompiling network")
                        manage_network(input_filename, build_options, reload_build)
                        log.info("Monitoring for updates...")
                    except Exception:
                        log.warning("Unable to build network")
                        traceback.print_exc()

        except KeyboardInterrupt:
            log.info("Exiting")

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
    nidb.copy_graphics(G_graphics)

    host = "nectar1"
    #junosphere_compiler = compiler.JunosphereCompiler(nidb, anm, host)
    #junosphere_compiler.compile()
    netkit_compiler = compiler.NetkitCompiler(nidb, anm, host)
    netkit_compiler.compile()
    #dynagen_compiler = compiler.DynagenCompiler(nidb, anm, host)
    #dynagen_compiler.compile()

    cisco_compiler = compiler.CiscoCompiler(nidb, anm, host)
    cisco_compiler.compile()

    return nidb

def deploy_network(nidb):
    #TODO: make this driven from config file
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
    dest_ip = dest_node.interfaces[0].ip_address # choose random interface on this node

    command = "traceroute -n -a -U -w 0.5 %s" % dest_ip 
    # abort after 10 fails, proceed on any success, 0.1 second timeout (quite aggressive)
    #command = 'vtysh -c "show ip route"'
    measure.send(nidb, "nectar1", command, remote_hosts)
    remote_hosts = [node.tap.ip for node in nidb.nodes("is_router") if node.bgp.ebgp_neighbors]
    command = "cat /var/log/zebra/bgpd.log"

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
