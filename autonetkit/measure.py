import autonetkit.log as log
import time
import textfsm
import pika
import json

def send(command, hosts, threads = 3):
# netaddr IP addresses not JSON serializable
    hosts = [str(h) for h in hosts]
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='115.146.94.68'))
    channel = connection.channel()

    channel.queue_declare(queue='measure')
    data = {
            'command': command,
            "hosts": hosts,
            "threads": threads,
            }
    body = json.dumps(data)
    channel.basic_publish(exchange='',
                        routing_key='measure',
                        body= body)
    connection.close()




