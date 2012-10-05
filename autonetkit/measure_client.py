import pika
import json
import pprint
import sys
import autonetkit.config as config

def main():
    server = sys.argv[1]
    pika_host = config.settings['Rabbitmq']['server']
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = pika_host))
    channel = connection.channel()

    channel.exchange_declare(exchange='measure',
            type='direct')

    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange='measure',
                       queue=queue_name,
                       routing_key = server)

    print ' [*] Waiting for messages. To exit press CTRL+C'

    def callback(ch, method, properties, body):
        data = json.loads(body)
        command = data['command']
        hosts = data['hosts']
        threads = data['threads']
        run_command(channel, command, hosts,  threads)

    channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

    channel.start_consuming()

def run_command(rmq_channel, command, hosts,  threads):
    """Execute command on remote host"""
    from Exscript import Account, Host
    from Exscript.util.start import start

    results = {}

    def do_something(thread, host, conn):
        #conn.execute('vtysh -c "%s"' % command)
        conn.execute(command)
        result = repr(conn.response)
        data = { host.address: {command: result}, }
        body = json.dumps(data)
        rmq_channel.basic_publish(exchange='measure',
                routing_key = "result",
                body= body)
        #conn.execute("exit")
        
    accounts = [Account("root", password = "1234")] 

    hosts = [Host(h, default_protocol = "ssh") for h in hosts]
#TODO: open multiple ssh sessions
    start(accounts, hosts, do_something, max_threads = threads)
    return results

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
