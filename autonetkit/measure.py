import autonetkit.log as log
import time
import textfsm
import pika
import json

def send():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='115.146.94.68'))
    channel = connection.channel()

    channel.queue_declare(queue='hello')

    a = {
            'test': [1, 2, 3, 4],
            'b': {'a': 11, 22:' bb'}
            }
    body = json.dumps(a)
    channel.basic_publish(exchange='',
                        routing_key='hello',
                        body= body)
    connection.close()


def run_command(host, username, remote_hosts, command, timeout = 30, key_filename = None):
    """Execute command on remote host"""
    from Exscript import Account
    from Exscript.util.start import start
    from Exscript.util.match import first_match, any_match
    from Exscript import PrivateKey
    from Exscript.util.template import eval_file
    from Exscript.protocols.Exception import InvalidCommandException

    results = {}

    def do_something(thread, host, conn):
        #res = eval_file(conn, "autonetkit/exscript/test.template")
        #import pprint
        #pprint.pprint(res)
        #print res.get("data")
        #for entry in res["data"]:
            #print entry
        #return
        for remote_host in remote_hosts:
            #TODO: multiplex this better
#TODO: this needs tap IPs....
            conn.execute("ssh root@%s" % remote_host)
            conn.execute("vtysh")
            conn.execute(command)
            #print "The response was", repr(conn.response)
            results[remote_host] = conn.response
            conn.execute("exit")
            conn.execute("logout")
        
    if key_filename:
        key = PrivateKey.from_file(key_filename)
        accounts = [Account(username, key = key)] 
    else:
        accounts = [Account(username)] 

    hosts = ['ssh://%s' % host]
#TODO: open multiple ssh sessions
    start(accounts, hosts, do_something, verbose = 1)
    return results

