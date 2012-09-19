import pika

#import pika.log
#pika.log.setup(pika.log.DEBUG, color=True)

class AnkPika(object):

    def __init__(self, host):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = host))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange='www',
                type='direct')


    def publish(self, exchange, routing_key, body):
        self.channel.basic_publish(exchange= exchange,
                routing_key = routing_key,
                body= body)

    def publish_compressed(self, exchange, routing_key, body):
        """Compresses body using zlib before sending"""
        import zlib
        body = zlib.compress(body, 9)
        self.publish(exchange, routing_key, body)

        #TODO: implement callback


