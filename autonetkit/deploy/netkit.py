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

def deploy(host, username, dst_folder):
    tar_file = package(dst_folder)
    transfer(host, username, tar_file)
    extract(host, username, tar_file, dst_folder)

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
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy( paramiko.AutoAddPolicy())
    if key_filename:
        log.debug("Connecting to %s with %s and key %s" % (host, username, key_filename))
        ssh.connect(host, username = username, key_filename = key_filename)
    else:
        log.info("Connecting to %s with %s" % (host, username))
        ssh.connect(host, username = username)
    log.debug("Opening SSH for SFTP")
    ftp = ssh.open_sftp()
    log.debug("Putting file %s to %s" % (local, remote))
    ftp.put(local, remote)
    log.debug("Put file %s to %s" % (local, remote))
    ftp.close()

def extract(host, username, tar_file, cd_dir, timeout = 30, key_filename = None, verbosity = 0):
    """Extract and start lab"""
    log.debug("Extracting and starting lab on %s" % (host))
    log.info("Extracting and starting Netkit lab")
    from Exscript import Account
    from Exscript.util.start import start
    from Exscript.util.match import first_match
    from Exscript import PrivateKey
    from Exscript.protocols.Exception import InvalidCommandException

    messaging = ank_messaging.AnkMessaging()

    def starting_host(protocol, index, data):
        m = re.search('\\"(\S+)\\"', data.group(index))
        if m:
            hostname = m.group(1)
            log.info(data.group(index)) #TODO: use regex to strip out just the machine name
            body = {"starting": hostname}
            messaging.publish_json(body)

    def lab_started(protocol, index, data):
        log.info("Lab started on %s" % host)
        body = {"lab started": host}
        messaging.publish_json(body)

    def make_not_found(protocol, index, data):
        log.warning("Make not installed on remote host %s. Please install make and retry." % host)
        return

    def start_lab(thread, host, conn):
        conn.set_timeout(timeout)
        conn.add_monitor(r'Starting (\S+)', starting_host)
        conn.add_monitor(r'The lab has been started', lab_started)
        conn.add_monitor(r'make: not found', make_not_found)
        #conn.data_received_event.connect(data_received)
        conn.execute('cd %s' % cd_dir)
        conn.execute('lcrash -k')
        conn.execute("lclean")
        conn.execute('cd') # back to home directory tar file copied to
        conn.execute('tar -xzf %s' % tar_file)
        conn.execute('cd %s' % cd_dir)
        conn.execute('vlist')
        conn.execute("lclean")
        log.info("Starting lab")
        start_command = 'lstart -p5 -o --con0=none'
        try:
            conn.execute(start_command)
        except InvalidCommandException, error:
            if "already running" in str(error):
                time.sleep(1)
                conn.execute(start_command)
        first_match(conn, r'^The lab has been started')
        conn.send("exit")

    if key_filename:
        key = PrivateKey.from_file(key_filename)
        log.debug("Connecting to %s with username %s and key %s" % (host, username, key_filename))
        accounts = [Account(username, key = key)] 
    else:
        log.debug("Connecting to %s with username %s" % (host, username))
        accounts = [Account(username)] 

    hosts = ['ssh://%s' % host]
    start(accounts, hosts, start_lab, verbose = verbosity)
