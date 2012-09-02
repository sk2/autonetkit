import pika
import json
import pprint

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='115.146.94.68'))
    channel = connection.channel()


    channel.queue_declare(queue='measure')

    print ' [*] Waiting for messages. To exit press CTRL+C'

    def callback(ch, method, properties, body):
        data = json.loads(body)
        pprint.pprint(data)
        command = data['command']
        hosts = data['hosts']
        threads = data['threads']
        run_command(channel, command, hosts,  threads)
        #print " [x] Received %r" % (body,)

    channel.basic_consume(callback,
                        queue='measure',
                        no_ack=True)

    channel.start_consuming()

def run_command(rmq_channel, command, hosts,  threads):
    """Execute command on remote host"""
    from Exscript import Account, Host
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
            conn.execute("vtysh")
            conn.execute(command)
            #print "The response was", repr(conn.response)
            result = conn.response
            body = {
                    (command, host): result,
                    }
            rmq_channel.basic_publish(exchange='',
                    routing_key='measure',
                    body= body)

            conn.execute("exit")
            conn.execute("logout")
        
    accounts = [Account("root")] 

    hosts = [Host(h, default_protocol = "ssh") for h in hosts]
#TODO: open multiple ssh sessions
    start(accounts, hosts, do_something, verbose = 2)
    return results

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
