import autonetkit.config as config
import autonetkit.log as log

use_rabbitmq = config.settings['Rabbitmq']['active']
if use_rabbitmq:
    import pika

#TODO: tidy this to be a try/except ImportError

#import pika.log
#pika.log.setup(pika.log.DEBUG, color=True)

class AnkPika(object):

    def __init__(self, host):
        if use_rabbitmq:
            log.debug("Using Rabbitmq with server %s " % host)
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host = host))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange='www',
                    type='direct')
        else:
            log.debug("Not using Rabbitmq")
            self.publish = self.publish_blank_stub
            self.publish_compressed = self.publish_blank_stub


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
    def publish_blank_stub(self, exchange, routing_key, body):
        """use if not using rabbitmq, simplifies calls elsewhere (publish does nothing)"""
#TODO: log that not sending for debug purposes
        return


