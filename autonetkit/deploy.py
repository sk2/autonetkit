import autonetkit.log as log
import time

def package(src_dir, target):
    log.info("Packaging %s" % src_dir)
    import tarfile
    import os
    tar_filename = "%s.tar.gz" % target
#time.strftime("%Y%m%d_%H%M", time.localtime())
    tar = tarfile.open(os.path.join(tar_filename), "w:gz")
    tar.add(src_dir)
    tar.close()
    print tar_filename
    return tar_filename


def transfer(host, username, local, remote, key_filename = None):
    log.info("Transferring lab to %s" % host)
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy())
    if key_filename:
        ssh.connect(host, username = username, key_filename = key_filename)
    else:
        ssh.connect(host, username = username)
    ftp = ssh.open_sftp()
    ftp.put(local, remote)
    ftp.close()

def extract(host, username, tar_file, cd_dir, timeout = 30, key_filename = None):
    from Exscript import Account
    from Exscript.util.start import start
    from Exscript.util.match import first_match
    from Exscript import PrivateKey
    from Exscript.protocols.Exception import InvalidCommandException

    def starting_host(protocol, index, data):
        #print "Starting", data.group(index)
        pass
#TODO: send to rabbitmq

    def lab_started(protocol, index, data):
        print "Lab started"

    def do_something(thread, host, conn):
        conn.set_timeout(timeout)
        conn.add_monitor(r'Starting (\S+)', starting_host)
        conn.add_monitor(r'The lab has been started', lab_started)
        #conn.data_received_event.connect(data_received)
        conn.execute('cd %s' % cd_dir)
        conn.execute('lcrash')
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
        accounts = [Account(username, key = key)] 
    else:
        accounts = [Account(username)] 


    hosts = ['ssh://%s' % host]
    start(accounts, hosts, do_something, verbose = 2)

