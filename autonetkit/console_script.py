from nidb import NIDB
import render
import random
import pprint
import traceback
from datetime import datetime
import os
import time
import compiler
import pkg_resources
import autonetkit.log as log
import autonetkit.ank_pika as ank_pika
import autonetkit.config as config

#import autonetkit.bgp_pol as bgp_pol
#raise SystemExit

#TODO: make if measure set, then not compile - or warn if both set, as don't want to regen topology when measuring

try:
    ank_version = pkg_resources.get_distribution("autonetkit-v3-dev").version
except pkg_resources.DistributionNotFound:
    ank_version = "dev"

class FileMonitor(object):
    """Lightweight polling-based monitoring to see if file has changed"""
    def __init__(self, filename):
        self.filename = filename
        try:
            self.last_timestamp = os.stat(filename).st_mtime
        except OSError:
            log.debug("Unable to read file %s, disabling monitoring" % filename)
            self.has_changed = self.return_false #TODO: use a lambda for succintness

    def return_false(self):
        """Used if unable to load file to monitor"""
        return False

    def has_changed(self):
        """Returns if file has changed since last called"""
        timestamp = os.stat(self.filename).st_mtime
        if timestamp > self.last_timestamp:
            self.last_timestamp = timestamp
            return True
        return False

def manage_network(input_graph_string, timestamp, build_options, reload_build=False):
    import build_network
    if reload_build:
# remap?
        build_network = reload(build_network)
    settings = config.settings

    rabbitmq_server = settings['Rabbitmq']['server']
    pika_channel = ank_pika.AnkPika(rabbitmq_server)

    if build_options['compile']:
        anm = build_network.build(input_graph_string, timestamp)
        

        if build_options['archive']:
            anm.save()
        nidb = compile_network(anm)
        import autonetkit.ank_json
        body = autonetkit.ank_json.dumps(anm, nidb)
        pika_channel.publish_compressed("www", "client", body)
        log.debug("Sent ANM to web server")
        if build_options['archive']:
            nidb.save()
        #render.remove_dirs(["rendered"])
        render.render(nidb)

    else:
        import autonetkit.anm
        anm = autonetkit.anm.AbstractNetworkModel()
        anm.restore_latest()
        nidb = NIDB()
        nidb.restore_latest()
        body = autonetkit.ank_json.dumps(anm, nidb)
        pika_channel.publish_compressed("www", "client", body)

    if build_options['diff']:
        import autonetkit.diff
        nidb_diff = autonetkit.diff.nidb_diff()
        import ank_json
        import json
        data = json.dumps(nidb_diff, cls=ank_json.AnkEncoder, indent = 4)
        log.info("Wrote diff to diff.json")
        with open("diff.json", "w") as fh: #TODO: make file specified in config
            fh.write(data)

    build_options.update(settings['General']) # update in case build has updated, eg for deploy
    build_options.update(settings['General']) # update in case build has updated, eg for deploy
    
    if build_options['deploy']:
        deploy_network(nidb, input_graph_string)

    if build_options['measure']:
        measure_network(nidb)

def parse_options():
    import argparse
    usage = "autonetkit -f input.graphml\n www.autonetkit.org"
    version="%(prog)s " + str(ank_version)
    parser = argparse.ArgumentParser(description = usage, version = version)

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--file', '-f', default= None, help="Load topology from FILE")        
    input_group.add_argument('--stdin',  action="store_true", default= False, help="Load topology from STDIN")        


    #TODO: move from -f to -i for --input
    parser.add_argument('--monitor', '-m',  action="store_true", default= False, 
            help="Monitor input file for changes")        
    parser.add_argument('--debug',  action="store_true", default= False, help="Debug mode")        
    parser.add_argument('--diff',  action="store_true", default= False, help="Diff NIDB")        
    parser.add_argument('--compile',  action="store_true", default= False, help="Compile")        
    parser.add_argument('--render',  action="store_true", default= False, help="Compile")        
    parser.add_argument('--deploy',  action="store_true", default= False, help="Deploy")        
    parser.add_argument('--archive',  action="store_true", default= False, help="Archive ANM, NIDB, and IP allocations")        
    parser.add_argument('--measure',  action="store_true", default= False, help="Measure")        
    parser.add_argument('--webserver',  action="store_true", default= False, help="Webserver")        
    arguments = parser.parse_args()
    return arguments

def main():
    settings = config.settings

    options = parse_options()
    log.info("AutoNetkit %s" % ank_version)

#TODO: only allow monitor mode with options.file not options.stdin

    if options.debug or settings['General']['debug']:
        #TODO: fix this
        import logging
        logger = logging.getLogger("ANK")
        logger.setLevel(logging.DEBUG)

    build_options = {
            'compile':  options.compile or settings['General']['compile'],
            'deploy': options.deploy or settings['General']['deploy'],
            'measure': options.measure or settings['General']['measure'],
            'monitor': options.monitor or settings['General']['monitor'],
            'diff': options.diff or settings['General']['diff'],
            'archive': options.archive or settings['General']['archive'],
            }

    if options.webserver:
        log.info("Webserver not yet supported, please run as seperate module")

    if options.file:
        with open(options.file, "r") as fh:
            input_string = fh.read()
        timestamp =  os.stat(options.file).st_mtime
    if options.stdin:
        import sys
        input_string = sys.stdin
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")

    manage_network(input_string, timestamp, build_options = build_options)

#TODO: work out why build_options is being clobbered for monitor mode
    build_options['monitor'] = options.monitor or settings['General']['monitor']

    if build_options['monitor']:
        try:
            log.info("Monitoring for updates...")
            input_filemonitor = FileMonitor(options.file)
            build_filemonitor = FileMonitor("autonetkit/build_network.py")
            while True:
                time.sleep(1)
                rebuild = False
                reload_build = False
                if input_filemonitor.has_changed():
                    print "input changed"
                    rebuild = True
                if build_filemonitor.has_changed():
                    reload_build = True
                    rebuild = True

                if rebuild:
                    try:
                        log.info("Input graph updated, recompiling network")
                        with open(options.file, "r") as fh:
                            input_string = fh.read() # read updates
                        manage_network(input_string, timestamp, build_options, reload_build)
                        log.info("Monitoring for updates...")
                    except Exception:
                        log.warning("Unable to build network")
                        traceback.print_exc()

        except KeyboardInterrupt:
            #TODO: need to close filehandles for input and output
            log.info("Exiting")

def compile_network(anm):
    nidb = NIDB() 
    G_phy = anm.overlay.phy
    G_ip = anm.overlay.ip
    G_graphics = anm.overlay.graphics
#TODO: build this on a platform by platform basis
    nidb.add_nodes_from(G_phy, retain=['label', 'host', 'platform', 'Network', 'update'])

    cd_nodes = [n for n in G_ip.nodes("collision_domain") if not n.is_switch] # Only add created cds - otherwise overwrite host of switched
    nidb.add_nodes_from(cd_nodes, retain=['label', 'host'], collision_domain = True)
# add edges to switches
    edges_to_add = [edge for edge in G_phy.edges() if edge.src.is_switch or edge.dst.is_switch]
    edges_to_add += [edge for edge in G_ip.edges() if edge.src.collision_domain or edge.dst.collision_domain]
    nidb.add_edges_from(edges_to_add, retain='edge_id')

#TODO: boundaries is still a work in progress...
    nidb.copy_graphics(G_graphics)

    #junosphere_compiler = compiler.JunosphereCompiler(nidb, anm, host)
    #junosphere_compiler.compile()
    #host = "nectar1"
    #netkit_compiler = compiler.NetkitCompiler(nidb, anm, host)
    #netkit_compiler.compile()

    host = "localhost"
    if any(G_phy.nodes(host = host, platform = "netkit")):
        netkit_compiler = compiler.NetkitCompiler(nidb, anm, host)
        netkit_compiler.compile()

#TODO: map this to all hosts present in config. By default include "internal" for each platform
    host = "internal"
    if any(G_phy.nodes(host = host, platform = "cisco")):
        cisco_compiler = compiler.CiscoCompiler(nidb, anm, host)
        cisco_compiler.compile()

    return nidb

def deploy_network(nidb, input_graph_string):
    import autonetkit.deploy.netkit as netkit_deploy
    import autonetkit.deploy.cisco as cisco_deploy
    #TODO: make this driven from config file
    log.info("Deploying network")

#TODO: pick up platform, host, filenames from nidb (as set in there)
    deploy_hosts = config.settings['Deploy Hosts']
    for hostname, host_data in deploy_hosts.items():
        for platform, platform_data in host_data.items():

            if not platform_data['deploy']:
                log.debug("Not deploying to %s on %s" % (platform, hostname))
                continue

            config_path = os.path.join("rendered", hostname, platform)

            if hostname == "internal":
                if platform == "cisco":
                    try:
                        import autonetkit.deploy.worm as worm_deploy
                    except ImportError:
                        continue # development module, may not be available

                    worm_deploy.package(nidb, config_path, input_graph_string)

                continue

            username = platform_data['username']
            key_file = platform_data['key file']
            host = platform_data['host']
            
            if platform == "netkit" :
                tar_file = netkit_deploy.package(config_path, "nklab")
                netkit_deploy.transfer(host, username, tar_file, tar_file, key_file)
                netkit_deploy.extract(host, username, tar_file, config_path, timeout = 60, key_filename= key_file)
            if platform == "cisco":
                cisco_deploy.package(config_path, "nklab")

def measure_network(nidb):
    import measure
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
