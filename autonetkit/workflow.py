#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

import autonetkit
import autonetkit.ank_json as ank_json
import autonetkit.config as config
import autonetkit.log as log
import autonetkit.render as render
from autonetkit.nidb import DeviceModel


import cProfile

# from https://zapier.com/engineering/profiling-python-boss/


def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            # profile.print_stats()
            profile.dump_stats("profile")
    return profiled_func


def file_monitor(filename):
    """Generator based function to check if a file has changed"""

    last_timestamp = os.stat(filename).st_mtime

    while True:
        timestamp = os.stat(filename).st_mtime
        if timestamp > last_timestamp:
            last_timestamp = timestamp
            yield True
        yield False


#@do_cprofile
def manage_network(input_graph_string, timestamp, build=True,
                   visualise=True, compile=True, validate=True, render=True,
                   monitor=False, deploy=False, measure=False, diff=False,
                   archive=False, grid=None, ):
    """Build, compile, render network as appropriate"""

    # import build_network_simple as build_network

    import autonetkit.build_network as build_network

    if build:
        if input_graph_string:
            graph = build_network.load(input_graph_string)
        elif grid:
            graph = build_network.grid_2d(grid)

        # TODO: integrate the code to visualise on error (enable in config)
        anm = None
        try:
            anm = build_network.build(graph)
        except Exception, e:
            # Send the visualisation to help debugging
            try:
                if visualise:
                    import autonetkit
                    autonetkit.update_vis(anm)
            except Exception, e:
                # problem with vis -> could be coupled with original exception -
                # raise original
                log.warning("Unable to visualise: %s" % e)
            raise  # raise the original exception
        else:
            if visualise:
                # log.info("Visualising network")
                import autonetkit
                autonetkit.update_vis(anm)

        if not compile:
            # autonetkit.update_vis(anm)
            pass

        if validate:
            import autonetkit.ank_validate
            try:
                autonetkit.ank_validate.validate(anm)
            except Exception, e:
                log.warning('Unable to validate topologies: %s' % e)
                log.debug('Unable to validate topologies',
                          exc_info=True)

    if compile:
        if archive:
            anm.save()
        nidb = compile_network(anm)
        autonetkit.update_vis(anm, nidb)

        #autonetkit.update_vis(anm, nidb)
        log.debug('Sent ANM to web server')
        if archive:
            nidb.save()

        # render.remove_dirs(["rendered"])

        if render:
            import time
            #start = time.clock()
            autonetkit.render.render(nidb)
            # print time.clock() - start
            #import autonetkit.render2
            #start = time.clock()
            # autonetkit.render2.render(nidb)
            # print time.clock() - start

    if not (build or compile):

        # Load from last run

        import autonetkit.anm
        anm = autonetkit.anm.NetworkModel()
        anm.restore_latest()
        nidb = DeviceModel()
        nidb.restore_latest()
        #autonetkit.update_vis(anm, nidb)

    if diff:
        import autonetkit.diff
        nidb_diff = autonetkit.diff.nidb_diff()
        import json
        data = json.dumps(nidb_diff, cls=ank_json.AnkEncoder, indent=4)
        # log.info('Wrote diff to diff.json')

        # TODO: make file specified in config

        with open('diff.json', 'w') as fh:
            fh.write(data)

    if deploy:
        deploy_network(anm, nidb, input_graph_string)

    log.info('Configuration engine completed')  # TODO: finished what?


#@do_cprofile
def compile_network(anm):
    # log.info("Creating base network model")
    nidb = create_nidb(anm)
    g_phy = anm['phy']
    # log.info("Compiling to targets")

    for target_data in config.settings['Compile Targets'].values():
        host = target_data['host']
        platform = target_data['platform']
        if platform == 'netkit':
            import autonetkit.compilers.platform.netkit as pl_netkit
            platform_compiler = pl_netkit.NetkitCompiler(nidb, anm,
                                                         host)
        elif platform == 'VIRL':
            try:
                import autonetkit_cisco.compilers.platform.cisco as pl_cisco
                platform_compiler = pl_cisco.CiscoCompiler(nidb, anm,
                                                           host)
            except ImportError:
                log.debug('Unable to load VIRL platform compiler')
        elif platform == 'dynagen':
            import autonetkit.compilers.platform.dynagen as pl_dynagen
            platform_compiler = pl_dynagen.DynagenCompiler(nidb, anm,
                                                           host)
        elif platform == 'junosphere':
            import autonetkit.compilers.platform.junosphere as pl_junosphere
            platform_compiler = pl_junosphere.JunosphereCompiler(nidb,
                                                                 anm, host)

        if any(g_phy.nodes(host=host, platform=platform)):
            # log.info('Compiling configurations for %s on %s'
                     # % (platform, host))
            platform_compiler.compile()  # only compile if hosts set
        else:
            log.debug('No devices set for %s on %s' % (platform, host))

    return nidb


def create_nidb(anm):

    # todo: refactor this now with the layer2/layer2_bc graphs - what does nidb need?
    # probably just layer2, and then allow compiled to access layer2_bc if
    # need (eg netkit?)

    nidb = DeviceModel(anm)


    return nidb


def deploy_network(anm, nidb, input_graph_string=None):

    # log.info('Deploying Network')

    deploy_hosts = config.settings['Deploy Hosts']
    for (hostname, host_data) in deploy_hosts.items():
        for (platform, platform_data) in host_data.items():
            if not any(nidb.nodes(host=hostname, platform=platform)):
                log.debug('No hosts for (host, platform) (%s, %s), skipping deployment'
                          % (hostname, platform))
                continue

            if not platform_data['deploy']:
                log.debug('Not deploying to %s on %s' % (platform,
                                                         hostname))
                continue

            config_path = os.path.join('rendered', hostname, platform)

            if hostname == 'internal':
                try:
                    from autonetkit_cisco import deploy as cisco_deploy
                except ImportError:
                    pass  # development module, may not be available
                if platform == 'VIRL':
                    create_new_xml = False
                    if not input_graph_string:
                        create_new_xml = True  # no input, eg if came from grid
                    elif anm['input'].data['file_type'] == 'graphml':
                        create_new_xml = True  # input from graphml, create XML

                    if create_new_xml:
                        cisco_deploy.create_xml(anm, nidb,
                                                input_graph_string)
                    else:
                        cisco_deploy.package(nidb, config_path,
                                             input_graph_string)
                continue

            username = platform_data['username']
            key_file = platform_data['key_file']
            host = platform_data['host']

            if platform == 'netkit':
                import autonetkit.deploy.netkit as netkit_deploy
                tar_file = netkit_deploy.package(config_path, 'nklab')
                netkit_deploy.transfer(host, username, tar_file,
                                       tar_file, key_file)
                netkit_deploy.extract(
                    host,
                    username,
                    tar_file,
                    config_path,
                    timeout=60,
                    key_filename=key_file,
                    parallel_count=10,
                )
                if platform == 'VIRL':

                    # TODO: check why using nklab here

                    cisco_deploy.package(config_path, 'nklab')
