import autonetkit.log as log
import time
import re
import autonetkit.config as config

def package(src_dir, target):
    log.info("Packaging %s" % src_dir)
    import tarfile
    import os
    tar_filename = "%s.tar.gz" % target
#time.strftime("%Y%m%d_%H%M", time.localtime())
    tar = tarfile.open(os.path.join(tar_filename), "w:gz")
    tar.add(src_dir)
    tar.close()
    return tar_filename

def transfer(host, username, local, remote, key_filename = None):
    log.debug("Transferring lab to %s" % host)
    log.info("Transferring Netkit lab")
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy())
# handle key_filename of '' (empty string)
    if not len(key_filename):
        key_filename = None
    if key_filename:
        log.debug("Connecting to %s with %s and key %s" % (host, username, key_filename))
        ssh.connect(host, username = username, key_filename = key_filename)
    else:
        log.debug("Connecting to %s with %s" % (host, username))
        ssh.connect(host, username = username, key_filename = key_filename)
        ssh.connect(host, username = username)
    log.debug("Opening SSH for SFTP")
    ftp = ssh.open_sftp()
    log.debug("Putting file %s to %s" % (local, remote))
    ftp.put(local, remote)
    log.debug("Put file %s to %s" % (local, remote))
    ftp.close()

def extract(host, username, tar_file, cd_dir, timeout = 30, key_filename = None):
    """Extract and start lab"""
    log.debug("Extracting and starting lab on %s" % (host))
    log.info("Extracting and starting Netkit lab")
    from Exscript import Account
    from Exscript.util.start import start
    from Exscript.util.match import first_match
    from Exscript import PrivateKey
    from Exscript.protocols.Exception import InvalidCommandException


    use_rabbitmq = config.settings['Rabbitmq']['active']
    if use_rabbitmq:
        import pika
        import json
        pika_host = config.settings['Rabbitmq']['server']
        www_connection = pika.BlockingConnection(pika.ConnectionParameters(
                host = pika_host))
        www_channel = www_connection.channel()
        www_channel.exchange_declare(exchange='www',
                type='direct')


    def starting_host(protocol, index, data):
        m = re.search('\\"(\S+)\\"', data.group(index))
#TODO: reverse lookup from foldername to the canonical id of device
        if m:
            hostname = m.group(1)
            log.info(data.group(index)) #TODO: use regex to strip out just the machine name
            body = {"starting": hostname}
            if use_rabbitmq:
                www_channel.basic_publish(exchange='www',
                        routing_key = "client",
                        body= json.dumps(body))

    def lab_started(protocol, index, data):
        body = {"lab started": host}
        if use_rabbitmq:
            www_channel.basic_publish(exchange='www',
                    routing_key = "client",
                    body= json.dumps(body))

    def do_something(thread, host, conn):
        conn.set_timeout(timeout)
        conn.add_monitor(r'Starting (\S+)', starting_host)
        conn.add_monitor(r'The lab has been started', lab_started)
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
                #print "Already Running" #TODO: handle appropriately
                #print "Halting previous lab"
                #conn.execute("vclean -K")
                #print "Halted previous lab"
                #conn.execute("vstart taptunnelvm --con0=none --eth0=tap,172.16.0.1,172.16.0.2") # TODO: don't hardcode this
                #print "Starting lab"
                conn.execute(start_command)
        first_match(conn, r'^The lab has been started')
        conn.send("exit")
#TODO: need to capture and handle tap startup

    if key_filename:
        key = PrivateKey.from_file(key_filename)
        log.debug("Connecting to %s with username %s and key %s" % (host, username, key_filename))
        accounts = [Account(username, key = key)] 
    else:
        log.debug("Connecting to %s with username %s" % (host, username))
        accounts = [Account(username)] 

    hosts = ['ssh://%s' % host]
    start(accounts, hosts, do_something, verbose = 0)
