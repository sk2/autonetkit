import autonetkit.render as render
import autonetkit.nidb
import random
import sys
import os
import autonetkit.log as log
import autonetkit.ank_messaging as ank_messaging

debug = 0
if debug:
    import logging
    log.logger.setLevel(logging.DEBUG)

def main():
    import argparse
    usage = "ank_measure_client"
    parser = argparse.ArgumentParser(description = usage)
    parser.add_argument('filename',  default= None, help="Input topology")   
    parser.add_argument('--deploy',  action="store_true", default= False, help="Deploy")        
    parser.add_argument('--measure',  action="store_true", default= False, help="Measure")        
    
    arguments = parser.parse_args()

    if arguments.filename:

        import build # grabs build.py from example
        anm = build.build_overlays(arguments.filename)
        anm.save()

        import compile # grabs compile.py from example
        nidb = build.build_nidb(anm)
        nidb.save()
        messaging = ank_messaging.AnkMessaging()
        messaging.publish_anm(anm, nidb)

        host = "localhost"
        nk_compiler = compile.NetkitCompiler(nidb, anm, host)
        nk_compiler.compile()

        render.render(nidb)
    else:
        log.info("No input file specified, attempting to load previously compiled network")
        # loading
        anm = autonetkit.anm.AbstractNetworkModel()
        anm.restore_latest()
        nidb = autonetkit.nidb.NIDB()
        nidb.restore_latest()

    username = "sk2"
    host = "192.168.255.129"
    if arguments.deploy:
        import autonetkit.deploy.netkit as nk_deploy
        dst_folder = nidb.topology['localhost'].render_dst_folder
        nk_deploy.deploy(host, username, dst_folder)
    
    if arguments.measure:
        """ Some notes on measurement:
        NOTE: Measure requires a remote host to be setup, and rabbitmq running, (by default ank will look on localhost)
 http://www.rabbitmq.com/install-debian.html

 or for OS X: http://superuser.com/questions/464311/open-port-5672-tcp-for-access-to-rabbitmq-on-mac

 and
 pip install pika
 pip install https://github.com/knipknap/exscript/tarball/master
 note this needs paramiko... which needs to compile. if you don't have python headers, eg in ubuntu: sudo apt-get install python-dev
 wget https://raw.github.com/sk2/autonetkit/master/autonetkit/measure_client.py
 sk2@ubuntu:~$ python measure_client.py --server 192.168.255.1
 where --server specifies the rabbitmq server
 can also use through ANK package:
 install ank through github, then install Exscript
 can then do:
 ank_measure_client --server 192.168.255.1
"""

        import autonetkit.measure as measure
        log.info("Measuring network")
        remote_hosts = [node.tap.ip for node in nidb.routers() ]
        #remote_hosts = remote_hosts[:3] # truncate for testing
        dest_node = random.choice(list(nidb.routers()))
        log.info("Tracing to randomly selected node: %s" % dest_node)
        dest_ip = dest_node.interfaces[0].ipv4_address # choose random interface on this node
        command = "traceroute -n -a -U -w 0.5 %s" % dest_ip 
        #command = 'vtysh -c "show ip route"'
        measure.send(nidb, command, remote_hosts, threads = 20)

        # abort after 10 fails, proceed on any success, 0.1 second timeout (quite aggressive)
        #command = 'vtysh -c "show ip route"'
        remote_hosts = [node.tap.ip for node in nidb.routers() if node.bgp.ebgp_neighbors]
        command = "cat /var/log/zebra/bgpd.log"
        #measure.send(nidb, command, remote_hosts)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
