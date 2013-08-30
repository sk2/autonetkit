"""Console script entry point for AutoNetkit"""

from autonetkit.nidb import NIDB
import autonetkit.render as render
import random
from autonetkit import update_http
import traceback
from datetime import datetime
import os
import time
import autonetkit.compiler as compiler
import pkg_resources
import autonetkit.log as log
import autonetkit.ank_messaging as ank_messaging
import autonetkit.config as config
import autonetkit.ank_json as ank_json

# TODO: make if measure set, then not compile - or warn if both set, as
# don't want to regen topology when measuring

try:
    ANK_VERSION = pkg_resources.get_distribution("autonetkit").version
except pkg_resources.DistributionNotFound:
    ANK_VERSION = "dev"

def file_monitor(filename):
    """Generator based function to check if a file has changed"""
    last_timestamp = os.stat(filename).st_mtime

    while True:
        timestamp = os.stat(filename).st_mtime
        if timestamp > last_timestamp:
            last_timestamp = timestamp
            yield True
        yield False

def manage_network(input_graph_string, timestamp, build_options, reload_build=False, grid = None):
    """Build, compile, render network as appropriate"""
    # import build_network_simple as build_network
    import autonetkit.build_network as build_network
    if reload_build:
# remap?
        build_network = reload(build_network)

    if build_options['build']:
        if input_graph_string:
            graph = build_network.load(input_graph_string)
        elif grid:
            graph = build_network.grid_2d(grid)

        anm = build_network.build(graph)
        if not build_options['compile']:
            update_http(anm)

        if build_options['validate']:
            import autonetkit.ank_validate
            autonetkit.ank_validate.validate(anm)

    if build_options['compile']:
        if build_options['archive']:
            anm.save()
        nidb = compile_network(anm)

        update_http(anm, nidb)
        log.debug("Sent ANM to web server")
        if build_options['archive']:
            nidb.save()
        # render.remove_dirs(["rendered"])
        if build_options['render']:
            render.render(nidb)

    if not(build_options['build'] or build_options['compile']):
        # Load from last run
        import autonetkit.anm
        anm = autonetkit.anm.AbstractNetworkModel()
        anm.restore_latest()
        nidb = NIDB()
        nidb.restore_latest()
        update_http(anm, nidb)

    if build_options['diff']:
        import autonetkit.diff
        nidb_diff = autonetkit.diff.nidb_diff()
        import json
        data = json.dumps(nidb_diff, cls=ank_json.AnkEncoder, indent=4)
        log.info("Wrote diff to diff.json")
        with open("diff.json", "w") as fh:  # TODO: make file specified in config
            fh.write(data)

    if build_options['deploy']:
        deploy_network(anm, nidb, input_graph_string)

    if build_options['measure']:
        measure_network(anm, nidb)

    log.info("Finished")

def parse_options(argument_string = None):
    """Parse user-provided options"""
    import argparse
    usage = "autonetkit -f input.graphml"
    version = "%(prog)s " + str(ANK_VERSION)
    parser = argparse.ArgumentParser(description=usage, version=version)

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--file', '-f', default=None, help="Load topology from FILE")
    input_group.add_argument('--stdin', action="store_true", default=False,
                             help="Load topology from STDIN")

    parser.add_argument(
        '--monitor', '-m', action="store_true", default=False,
        help="Monitor input file for changes")
    parser.add_argument('--debug', action="store_true",
                        default=False, help="Debug mode")
    parser.add_argument('--quiet', action="store_true",
                        default=False, help="Quiet mode (only display warnings and errors)")
    parser.add_argument('--diff', action="store_true", default=False,
                        help="Diff NIDB")
    parser.add_argument('--compile', action="store_true",
                        default=False, help="Compile")
    parser.add_argument(
        '--build', action="store_true", default=False, help="Build")
    parser.add_argument('--render', action="store_true", default=False, help="Compile")
    parser.add_argument('--validate', action="store_true", default=False, help="Validate")
    parser.add_argument('--deploy', action="store_true",
                        default=False, help="Deploy")
    parser.add_argument('--archive', action="store_true", default=False,
                        help="Archive ANM, NIDB, and IP allocations")
    parser.add_argument('--measure', action="store_true",
                        default=False, help="Measure")
    parser.add_argument('--webserver', action="store_true", default=False, help="Webserver")
    parser.add_argument('--grid', type=int, help="Grid Size (n * n)")
    parser.add_argument('--target', choices=['netkit', 'cisco'], default = None)
    parser.add_argument('--vis_uuid', default=None, help="UUID for multi-user visualisation")
    if argument_string:
        arguments = parser.parse_args(argument_string.split())
    else:
        # from command line arguments
        arguments = parser.parse_args()
    return arguments

def main(options):
    settings = config.settings

    if options.vis_uuid:
        config.settings['Http Post']['uuid'] = options.vis_uuid

    log.info("AutoNetkit %s" % ANK_VERSION)

    if options.target == "cisco":
        # output target is Cisco
        log.info("Setting output target as Cisco")
        settings['Graphml']['Node Defaults']['platform'] = "cisco"
        settings['Graphml']['Node Defaults']['host'] = "internal"
        settings['Graphml']['Node Defaults']['syntax'] = "ios_xr"
        settings['Compiler']['Cisco']['to memory'] = 1
        settings['General']['deploy'] = 1
        settings['Deploy Hosts']['internal'] = {'cisco':
                {'deploy': 1}}

    if options.debug or settings['General']['debug']:
        # TODO: fix this
        import logging
        logger = logging.getLogger("ANK")
        logger.setLevel(logging.DEBUG)

    if options.quiet or settings['General']['quiet']:
        import logging
        logger = logging.getLogger("ANK")
        logger.setLevel(logging.WARNING)

    build_options = {
        'compile': options.compile or settings['General']['compile'],
        'render': options.render or settings['General']['render'],
        'validate': options.validate or settings['General']['validate'],
        'build': options.build or settings['General']['build'],
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
        timestamp = os.stat(options.file).st_mtime
    elif options.stdin:
        import sys
        input_string = sys.stdin
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    elif options.grid:
        input_string = ""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    else:
        log.info("No input file specified. Exiting")
        raise SystemExit

    manage_network(input_string, timestamp, build_options=build_options, grid = options.grid)


# TODO: work out why build_options is being clobbered for monitor mode
    build_options['monitor'] = options.monitor or settings['General'][
        'monitor']

    if build_options['monitor']:
        try:
            log.info("Monitoring for updates...")
            input_filemonitor = file_monitor(options.file)
            #build_filemonitor = file_monitor("autonetkit/build_network.py")
            while True:
                time.sleep(1)
                rebuild = False
                reload_build = False
                if input_filemonitor.next():
                    rebuild = True
                #if build_filemonitor.next():
                    #reload_build = True
                    #rebuild = True

                if rebuild:
                    try:
                        log.info("Input graph updated, recompiling network")
                        with open(options.file, "r") as fh:
                            input_string = fh.read()  # read updates
                        manage_network(input_string,
                                       timestamp, build_options, reload_build)
                        log.info("Monitoring for updates...")
                    except Exception, e:
                        log.warning("Unable to build network %s" %e)
                        traceback.print_exc()

        except KeyboardInterrupt:
            log.info("Exiting")

def create_nidb(anm):
    nidb = NIDB()
    g_phy = anm['phy']
    g_ip = anm['ip']
    g_graphics = anm['graphics']
    nidb.add_nodes_from(
        g_phy, retain=['label', 'host', 'platform', 'Network', 'update'])

    cd_nodes = [n for n in g_ip.nodes(
        "collision_domain") if not n.is_switch]  # Only add created cds - otherwise overwrite host of switched
    nidb.add_nodes_from(
        cd_nodes, retain=['label', 'host'], collision_domain=True)

    for node in nidb.nodes("collision_domain"):
        ipv4_node = anm['ipv4'].node(node)
        if ipv4_node:
            node.ipv4_subnet = ipv4_node.subnet
            node.ipv6_subnet = ipv4_node['ipv6'].subnet

# add edges to switches
    edges_to_add = [edge for edge in g_phy.edges()
            if edge.src.is_switch or edge.dst.is_switch]
    edges_to_add += [edge for edge in g_ip.edges() if edge.split] # cd edges from split
    nidb.add_edges_from(edges_to_add, retain='edge_id')

    nidb.copy_graphics(g_graphics)

    return nidb

def compile_network(anm):
    nidb = create_nidb(anm)
    g_phy = anm['phy']

    for target, target_data in config.settings['Compile Targets'].items():
        host = target_data['host']
        platform = target_data['platform']
        if platform == "netkit":
            import autonetkit.compilers.platform.netkit as pl_netkit
            platform_compiler = pl_netkit.NetkitCompiler(nidb, anm, host)
        elif platform == "cisco":
            import autonetkit.compilers.platform.cisco as pl_cisco
            platform_compiler = pl_cisco.CiscoCompiler(nidb, anm, host)
        elif platform == "dynagen":
            import autonetkit.compilers.platform.dynagen as pl_dynagen
            platform_compiler = pl_dynagen.DynagenCompiler(nidb, anm, host)
        elif platform == "junosphere":
            import autonetkit.compilers.platform.junosphere as pl_junosphere
            platform_compiler = pl_junosphere.JunosphereCompiler(nidb, anm, host)

        if any(g_phy.nodes(host=host, platform=platform)):
            log.info("Compile for %s on %s" % (platform, host))
            platform_compiler.compile()  # only compile if hosts set
        else:
            log.debug("No devices set for %s on %s" % (platform, host))

    return nidb


def deploy_network(anm, nidb, input_graph_string = None):

    log.info("Deploying Network")

    deploy_hosts = config.settings['Deploy Hosts']
    for hostname, host_data in deploy_hosts.items():
        for platform, platform_data in host_data.items():
            if not any(nidb.nodes(host=hostname, platform=platform)):
                log.debug("No hosts for (host, platform) (%s, %s), skipping deployment"
                        % (hostname, platform))
                continue

            if not platform_data['deploy']:
                log.debug("Not deploying to %s on %s" % (platform, hostname))
                continue

            config_path = os.path.join("rendered", hostname, platform)

            if hostname == "internal":
                try:
                    from autonetkit_cisco import deploy as cisco_deploy
                except ImportError:
                    pass  # development module, may not be available
                if platform == "cisco":
                    create_new_xml = False
                    if not input_graph_string:
                        create_new_xml = True # no input, eg if came from grid
                    elif anm['input'].data['file_type'] == "graphml":
                        create_new_xml = True # input from graphml, create XML

                    if create_new_xml:
                        cisco_deploy.create_xml(anm, nidb, input_graph_string)
                    else:
                        cisco_deploy.package(nidb, config_path,
                         input_graph_string)
                continue

            username = platform_data['username']
            key_file = platform_data['key_file']
            host = platform_data['host']

            if platform == "netkit":
                import autonetkit.deploy.netkit as netkit_deploy
                tar_file = netkit_deploy.package(config_path, "nklab")
                netkit_deploy.transfer(
                    host, username, tar_file, tar_file, key_file)
                netkit_deploy.extract(host, username, tar_file,
                  config_path, timeout=60, key_filename=key_file,
                  parallel_count = 10)
                if platform == "cisco":
                    #TODO: check why using nklab here
                    cisco_deploy.package(config_path, "nklab")

def collect_sh_ip_route(anm, nidb, start_node = None):
    if not start_node:
        start_node = random.choice([n for n in nidb.nodes("is_router")])

    #TODO: move this to another module, eg measure
    import autonetkit.measure as measure
    import autonetkit.verify as verify
    import autonetkit
    command = 'vtysh -c "show ip route"'
    #TODO: make auto take tap ip if netkit platform node
    #TODO: auto make put into list if isinstance(remote_hosts, nidb_node)
    remote_hosts = [start_node.tap.ip]
    result = measure.send(nidb, command, remote_hosts)

    processed = []
    for line in result:
        processed.append([anm['ipv4'].node(n) for n in line])

    #TODO: move this into verify module
    verification_results = verify.igp_routes(anm, processed)
    processed_with_results = []
    for line in processed:
        prefix = str(line[-1].subnet)
        try:
            result = verification_results[prefix]
        except KeyError:
            result = False # couldn't find prefix
        processed_with_results.append({
            'path': line,
            'verified': result,
            })

    autonetkit.update_http(anm, nidb)
    ank_messaging.highlight([], [], processed_with_results)


def measure_network(anm, nidb):
    import autonetkit.measure as measure

    log.info("Measuring network")
    if 1:
        remote_hosts = [node.tap.ip for node in nidb.nodes("is_router")]
        dest_node = random.choice([n for n in nidb.nodes("is_l3device")])
        log.info("Tracing to randomly selected node: %s" % dest_node)
        dest_ip = dest_node.interfaces[0].ipv4_address  # choose random interface on this node
        command = "traceroute -n -a -U -w 0.5 %s" % dest_ip
        measure.send(nidb, command, remote_hosts, threads = 10)
    # abort after 10 fails, proceed on any success, 0.1 second timeout (quite aggressive)
    if 0:
        collect_sh_ip_route(anm, nidb)

    if 0:
        #measure.send(nidb, command, remote_hosts, threads = 5)
        remote_hosts = [node.tap.ip for node in nidb.nodes(
            "is_router") if node.bgp.ebgp_neighbors]
        command = "cat /var/log/zebra/bgpd.log"

def console_entry():
    """If come from console entry point"""
    args = parse_options()
    main(args)

if __name__ == "__main__":
    try:
        args = parse_options()
        main(args)
    except KeyboardInterrupt:
        pass
