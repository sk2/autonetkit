"""Console script entry point for AutoNetkit"""

import os
import sys
import time
import traceback
from datetime import datetime

import autonetkit.config as config
import autonetkit.log as log
import autonetkit.workflow as workflow
import pkg_resources

try:
    ANK_VERSION = pkg_resources.get_distribution("autonetkit").version
except pkg_resources.DistributionNotFound:
    ANK_VERSION = "dev"

def parse_options(argument_string=None):
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
                        help="Diff DeviceModel")
    parser.add_argument('--no_vis', dest="visualise",
        action="store_false", default=True,
        help="Visualise output")
    parser.add_argument('--compile', action="store_true",
                        default=False, help="Compile")
    parser.add_argument(
        '--build', action="store_true", default=False, help="Build")
    parser.add_argument(
        '--render', action="store_true", default=False, help="Compile")
    parser.add_argument(
        '--validate', action="store_true", default=False, help="Validate")
    parser.add_argument('--deploy', action="store_true",
                        default=False, help="Deploy")
    parser.add_argument('--archive', action="store_true", default=False,
                        help="Archive ANM, DeviceModel, and IP allocations")
    parser.add_argument('--measure', action="store_true",
                        default=False, help="Measure")
    parser.add_argument(
        '--webserver', action="store_true", default=False, help="Webserver")
    parser.add_argument('--grid', type=int, help="Grid Size (n * n)")
    parser.add_argument(
        '--target', choices=['netkit', 'cisco'], default=None)
    parser.add_argument(
        '--vis_uuid', default=None, help="UUID for multi-user visualisation")
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

    try:
        # test if can import, if not present will fail and not add to template
        # path
        import autonetkit_cisco
    except ImportError:
        pass
    else:
        import autonetkit_cisco.version
        version_banner = autonetkit_cisco.version.banner()
        log.info("%s" % version_banner)

    log.info("AutoNetkit %s" % ANK_VERSION)

    if options.target == "cisco":
        # output target is Cisco
        log.info("Setting output target as Cisco")
        settings['Graphml']['Node Defaults']['platform'] = "VIRL"
        settings['Graphml']['Node Defaults']['host'] = "internal"
        settings['Graphml']['Node Defaults']['syntax'] = "ios_xr"
        settings['Compiler']['Cisco']['to memory'] = 1
        settings['General']['deploy'] = 1
        settings['Deploy Hosts']['internal'] = {'VIRL':
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
        # use and for visualise as no_vis negates
        'visualise': options.visualise and settings['General']['visualise'],
    }

    if options.webserver:
        log.info("Webserver not yet supported, please run as seperate module")

    if options.file:
        with open(options.file, "r") as fh:
            input_string = fh.read()
        timestamp = os.stat(options.file).st_mtime
    elif options.stdin:
        input_string = sys.stdin
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    elif options.grid:
        input_string = ""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    else:
        log.info("No input file specified. Exiting")
        return

    try:
        workflow.manage_network(input_string, timestamp,
                       grid=options.grid, **build_options)
    except Exception, err:
        log.error(
            "Error generating network configurations: %s. More information may be available in the debug log." % err)
        log.debug("Error generating network configurations", exc_info=True)
        if settings['General']['stack_trace']:
            print traceback.print_exc()
        sys.exit("Unable to build configurations.")

# TODO: work out why build_options is being clobbered for monitor mode
    build_options['monitor'] = options.monitor or settings['General'][
        'monitor']

    if build_options['monitor']:
        try:
            log.info("Monitoring for updates...")
            input_filemonitor = workflow.file_monitor(options.file)
            #build_filemonitor = file_monitor("autonetkit/build_network.py")
            while True:
                time.sleep(1)
                rebuild = False
                if input_filemonitor.next():
                    rebuild = True

                if rebuild:
                    try:
                        log.info("Input graph updated, recompiling network")
                        with open(options.file, "r") as fh:
                            input_string = fh.read()  # read updates
                        workflow.manage_network(input_string,
                                       timestamp, build_options)
                        log.info("Monitoring for updates...")
                    except Exception, e:
                        log.warning("Unable to build network %s" % e)
                        traceback.print_exc()

        except KeyboardInterrupt:
            log.info("Exiting")

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
