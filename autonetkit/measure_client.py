import pika
import json
import pprint

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='115.146.94.68'))
    channel = connection.channel()


    channel.queue_declare(queue='hello')

    print ' [*] Waiting for messages. To exit press CTRL+C'

    def callback(ch, method, properties, body):
        data = json.loads(body)
        pprint.pprint(data)
        for key, val in data.items():
            print key, val
        #print " [x] Received %r" % (body,)

    channel.basic_consume(callback,
                        queue='hello',
                        no_ack=True)

    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
