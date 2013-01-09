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

    username = "sk2"
    host = "192.168.255.129"
    if False: # deploy
        import autonetkit.deploy.netkit as netkit_deploy
        config_path = os.path.join("rendered", "localhost", "netkit")

        tar_file = netkit_deploy.package(config_path, "nklab")
        netkit_deploy.transfer(host, username, tar_file)
        netkit_deploy.extract(host, username, tar_file, config_path, timeout = 60, verbosity = 1)
    
    if False: # measure
        #NOTE: Measure requires a remote host to be setup, and rabbitmq running, (by default ank will look on localhost)
# http://www.rabbitmq.com/install-debian.html

# and
# pip install pika
# wget https://raw.github.com/sk2/autonetkit/master/autonetkit/measure_client.py
# python measure_client.py
        import autonetkit.measure as measure
        log.info("Measuring network")
        remote_hosts = [node.tap.ip for node in nidb.nodes("is_router") ]
        dest_node = random.choice([n for n in nidb.nodes("is_l3device")])
        log.info("Tracing to randomly selected node: %s" % dest_node)
        dest_ip = dest_node.interfaces[0].ip_address # choose random interface on this node

        command = "traceroute -n -a -U -w 0.5 %s" % dest_ip 
        # abort after 10 fails, proceed on any success, 0.1 second timeout (quite aggressive)
        #command = 'vtysh -c "show ip route"'
        measure.send(nidb, host, command, remote_hosts)
        remote_hosts = [node.tap.ip for node in nidb.nodes("is_router") if node.bgp.ebgp_neighbors]
        command = "cat /var/log/zebra/bgpd.log"




if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
