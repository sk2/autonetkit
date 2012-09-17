import pika
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='115.146.94.68'))
channel = connection.channel()

channel.exchange_declare(exchange='www',
        type='direct')

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange='www',
                    queue=queue_name,
                    routing_key = "client")

print ' [*] Waiting for messages. To exit press CTRL+C'

def callback(ch, method, properties, body):
    import zlib
    body = zlib.decompress(body)
    print body

channel.basic_consume(callback,
                    queue=queue_name,
                    no_ack=True)

channel.start_consuming()
