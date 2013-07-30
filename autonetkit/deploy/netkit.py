import autonetkit.log as log
import time
import re
import autonetkit.config as config
import autonetkit.ank_messaging as ank_messaging

try:
    import Exscript
except ImportError:
    log.warning("Deployment requires Exscript: "
    "pip install https://github.com/knipknap/exscript/tarball/master")

def deploy(host, username, dst_folder, key_filename = None, parallel_count = 5):
    tar_file = package(dst_folder)
    transfer(host, username, tar_file, key_filename = key_filename)
    extract(host, username, tar_file, dst_folder, key_filename = key_filename,
        parallel_count = parallel_count)

def package(src_dir, target = "netkit_lab"):
    log.info("Packaging %s" % src_dir)
    import tarfile
    import os
    tar_filename = "%s.tar.gz" % target
    tar = tarfile.open(os.path.join(tar_filename), "w:gz")
    tar.add(src_dir)
    tar.close()
    return tar_filename

def transfer(host, username, local, remote = None, key_filename = None):
    log.debug("Transferring lab to %s" % host)
    log.info("Transferring Netkit lab")
    if not remote:
        remote = local # same filename
    import paramiko
    #import logging
    #logging.getLogger("paramiko").setLevel(logging.DEBUG)

    ssh = paramiko.SSHClient()
    #ssh.set_log_channel("ANK")
    ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy())
    if key_filename:
        log.debug("Connecting to %s with %s and key %s" % (host,
            username, key_filename))
        ssh.connect(host, username = username, key_filename = key_filename)
    else:
        log.info("Connecting to %s with %s" % (host, username))
        ssh.connect(host, username = username)
    log.info("Opening SSH for SFTP")
    ftp = ssh.open_sftp()
    log.info("Putting file %s tspoto %s" % (local, remote))
    ftp.put(local, remote)
    log.info("Put file %s to %s" % (local, remote))
    ftp.close()

def extract(host, username, tar_file, cd_dir, timeout = 45,
    key_filename = None, verbosity = 0, parallel_count = 5):
    """Extract and start lab"""
    log.debug("Extracting and starting lab on %s" % (host))
    log.info("Extracting and starting Netkit lab")
    from Exscript import Account
    from Exscript.util.start import start
    from Exscript.util.match import first_match
    from Exscript import PrivateKey
    from Exscript.protocols.Exception import InvalidCommandException

    messaging = ank_messaging

    def starting_host(protocol, index, data):
        log.info("Starting %s" % data.group(1))

    def lab_started(protocol, index, data):
        log.info("Lab started on %s" % host)
        messaging.publish_data(host, "lab started")

    def make_not_found(protocol, index, data):
        log.warning("Make not installed on remote host %s. Please install make and retry." % host)
        return

    def process_vlist(response):
        """Obtain VM to PID listing: required if terminating a numeric VM"""
        #TODO: could process using textfsm template
        vm_to_pid = {}
        for line in response.splitlines():
            match = re.match(r'^\w+\s+(\w+)\s+(\d+)', line)
            if match:
                vm = match.group(1)
                pid = match.group(2)
                vm_to_pid[vm] = pid

        return vm_to_pid

    def start_lab(thread, host, conn):
        conn.set_timeout(timeout)
        conn.add_monitor(r'Starting "(\w+)"', starting_host)
        conn.add_monitor(r'The lab has been started', lab_started)
        lab_vlist = []

        #conn.add_monitor(r'Virtual machine "((\S*_*)+)" is already running. Please', already_running_b)
        conn.add_monitor(r'make: not found', make_not_found)
        #conn.data_received_event.connect(data_received)


        conn.execute('cd %s' % cd_dir)
        conn.execute('lcrash -k')
        conn.execute("lclean")
        conn.execute('cd') # back to home directory tar file copied to
        conn.execute('tar -xzf %s' % tar_file)
        conn.execute('cd %s' % cd_dir)

        conn.execute("linfo")
        linfo_response = str(conn.response)
        vm_list = []
        for line in linfo_response.splitlines():
            if "The lab is made up of" in line:
                open_bracket = line.index("(")
                close_bracket = line.index(")")
                vm_list = line[open_bracket+1:close_bracket]
                vm_list = vm_list.split()
                log.info("The lab contains VMs %s" % ", ".join(vm_list))

        # now check if any vms are still running
        conn.execute("vlist")
        response = str(conn.response)
        lab_vlist = process_vlist(response)

        for virtual_machine in lab_vlist:
            if virtual_machine in vm_list:
                if virtual_machine.isdigit:
                    # convert to PID if numeric, as vcrash can't crash numeric ids (treats as PID)
                    crash_id = lab_vlist.get(virtual_machine)
                else:
                    crash_id = virtual_machine # use name

                if crash_id:
                    # crash_id may not be set, if machine not present in initial vlist, if so then ignore
                    log.info("Stopping running VM %s" % virtual_machine)
                    conn.execute("vcrash %s" % crash_id)

        conn.execute('vlist')
        conn.execute("lclean")
        start_command = 'lstart -p%s -o --con0=none' % parallel_count
        lab_is_started = False
        while lab_is_started == False:
            try:
                log.info("Starting lab")
                conn.execute(start_command)
            except InvalidCommandException, error:
                error_string = str(error)
                if "already running" in error_string:

                    conn.execute("vlist")
                    response = str(conn.response)
                    lab_vlist = process_vlist(response)

                    running_vms = []
                    for line in error_string.splitlines():
                        if "already running" in line:
                            running_vm = line.split('"')[1]
                            running_vms.append(running_vm)

                    for virtual_machine in running_vms:
                        if virtual_machine.isdigit:
                            # convert to PID if numeric, as vcrash can't crash numeric ids (treats as PID)
                            crash_id = lab_vlist.get(virtual_machine)
                        else:
                            crash_id = virtual_machine # use name

                        if crash_id:
                            # crash_id may not be set, if machine not present in initial vlist, if so then ignore
                            log.info("Stopping running VM %s" % virtual_machine)
                            conn.execute("vcrash %s" % crash_id)

                    time.sleep(1)
                    #conn.execute(start_command)
            else:
                lab_is_started = True
        first_match(conn, r'^The lab has been started')
        log.info("Lab started") #TODO: make this captured - need to debug capturing
        conn.send("exit")

    if key_filename:
        key = PrivateKey.from_file(key_filename)
        log.debug("Connecting to %s with username %s and key %s" % (host,
            username, key_filename))
        accounts = [Account(username, key = key)]
    else:
        log.debug("Connecting to %s with username %s" % (host, username))
        accounts = [Account(username)]

    hosts = ['ssh://%s' % host]
    verbosity = -1
    start(accounts, hosts, start_lab, verbose = verbosity)
