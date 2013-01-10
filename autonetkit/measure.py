import autonetkit.log as log
import pika
import json
import autonetkit.plugins.process_data as process_data
import autonetkit.config as config
import autonetkit.ank_messaging as ank_messaging
import autonetkit.log as log


def send(nidb, command, hosts, server = "measure_client", threads = 3):
# netaddr IP addresses not JSON serializable
    hosts = [str(h) for h in hosts]

    pika_host = config.settings['Rabbitmq']['server']

    messaging = ank_messaging.AnkMessaging()

    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host= pika_host))
        channel = connection.channel()

        channel.exchange_declare(exchange='measure',
                type='direct')
    except pika.exceptions.AMQPConnectionError:
        log.warning("Unable to connect to RabbitMQ on %s, exiting measurement" % pika_host)
        return

    data = {
            'command': command,
            "hosts": hosts,
            "threads": threads,
            }

    body = json.dumps(data)
    channel.basic_publish(exchange='measure',
            routing_key = server,
            body= body)
    #connection.close()

    hosts_received = set(hosts)

    # parsing function mappings
    parsing = {
            'vtysh -c "show ip route"': process_data.sh_ip_route,
            "traceroute": process_data.traceroute,
            }
    
    def callback(ch, method, properties, body):
        #TODO: send update to tornado web queue...
        data = json.loads(body)
        for host, host_data in data.items():
            for command, command_result in host_data.items():
                command_result = command_result.replace("\\r\\n", "\n")
                if command in parsing:
                    log.info( "%s %s" % (host, command))
                    parse_command = parsing[command]
                    parse_command(nidb, command_result)
                elif "traceroute" in command:
                    dst = command.split()[-1]   # last argument is the dst ip
                    src_host = process_data.reverse_tap_lookup(nidb, host)
                    dst_host = process_data.reverse_lookup(nidb, dst)
                    log.info("Trace from %s to %s" % (src_host, dst_host[1]))
                    parse_command = parsing["traceroute"]
                    log.info(command_result)
                    trace_result = parse_command(nidb, command_result)
                    trace_result.insert(0, src_host) 
                    log.info(trace_result)
                    if str(trace_result[-1]) == str(dst_host[1]): #TODO: fix so direct comparison, not string, either here or in anm object comparison: eg compare on label?
#TODO: make this use custom ANK serializer function
                        trace_result = [str(t.id) for t in trace_result if t] # make serializable
                        body = {"path": trace_result}
                        messaging.publish_json(body)
                    else:
                        log.info("Partial trace, not sending to webserver: %s", trace_result)
                else:
                    print "No parser defined for command %s" % command
                    print "Raw output:"
                    print command_result

            if host in hosts_received:
                hosts_received.remove(host) # remove from list of waiting hosts

            if not len(hosts_received):
                channel.stop_consuming()


    # wait for responses
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='measure',
                       queue=queue_name,
                       routing_key="result")

    channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

    channel.start_consuming()


