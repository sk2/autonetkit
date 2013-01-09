from autonetkit.nidb import NIDB
import autonetkit.render as render
import random
import sys
import pprint
import traceback
from datetime import datetime
import os
import time
import compiler
import pkg_resources
import autonetkit.log as log
import autonetkit.ank_messaging as ank_messaging
import autonetkit.config as config

debug = 1
if debug:
    import logging
    log.logger.setLevel(logging.DEBUG)

def main():
    try:
        filename = sys.argv[1]
    except IndexError:
        print "Please specify a filename"

    with open(filename, "r") as fh:
        input_string = fh.read()
    timestamp =  os.stat(filename).st_mtime

    import build
    anm = build.build_overlays(input_string, timestamp)
    import compile

    messaging = ank_messaging.AnkMessaging()
    nidb = build.build_nidb(anm)
    messaging.publish_anm(anm, nidb)

    host = "localhost"
    nk_compiler = compile.NetkitCompiler(nidb, anm, host)
    nk_compiler.compile()

    render.render(nidb)

    import autonetkit.deploy.netkit as netkit_deploy
    config_path = os.path.join("rendered", host, "netkit")
    username = "sk2"
    host = "192.168.255.129"
    tar_file = netkit_deploy.package(config_path, "nklab")
    netkit_deploy.transfer(host, username, tar_file)
    netkit_deploy.extract(host, username, tar_file, config_path, timeout = 60, verbosity = 1)
    
def deploy_network(nidb, input_graph_string):
    import autonetkit.deploy.netkit as netkit_deploy
    try:
        from autonetkit_cisco import deploy as cisco_deploy
    except ImportError:
        pass # development module, may not be available
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
                    cisco_deploy.package(nidb, config_path, input_graph_string)
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
