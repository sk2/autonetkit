# based on http://reminiscential.wordpress.com/2012/04/07/realtime-notification-delivery-using-rabbitmq-tornado-and-websocket/
try:
    import pika
    from pika.adapters.tornado_connection import TornadoConnection
except ImportError:
    pass # no pika installed, module will handle accordingly 
import tornado
import tornado.websocket as websocket
from tornado.netutil import TCPServer
import os
import json
import glob
import sys
import autonetkit.config as ank_config
import logging
import pkg_resources
www_dir = pkg_resources.resource_filename(__name__, "www_vis")

class EchoServer(TCPServer):
    def __init__(self, io_loop=None, ssl_options=None, ank_accessor = None, **kwargs):
        logging.info('a echo tcp server is started')
        self.event_listeners = set([])
        self.ank_accessor = ank_accessor
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)

    def handle_stream(self, stream, address):
        EchoConnection(stream, address, self.event_listeners, self.ank_accessor)

    def add_event_listener(self, listener):
        self.event_listeners.add(listener)
        print('PikaClient: listener %s added' % repr(listener))
 
    def remove_event_listener(self, listener):
        #TODO: check this works....
        print "removed listener"
        self.event_listeners.remove(listener)
        print('PikaClient: listener %s removed' % repr(listener))

class EchoConnection(object):
    stream_set = set([])
    def __init__(self, stream, address, event_listeners, ank_accessor):
        #TODO: look if can use initialize to remove internal params (boilerplate)
        logging.info('receive a new connection from %s', address)
        self.stream = stream
        self.address = address
        self.stream_set.add(self.stream)
        #self.stream.set_close_callback(self._on_close)
        #self.stream.read_until('__end__', self._on_read_line)
        self.stream.read_until_close(self._on_close)
        self.event_listeners = event_listeners
        self.ank_accessor = ank_accessor

    def _on_close(self, data):
        #TODO: check this is called
        body_parsed = json.loads(data)
        if body_parsed.has_key("anm"):
            print "Received updated network topology"
            try:
                self.ank_accessor.anm = body_parsed['anm']
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners("overlays")
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e
        elif body_parsed.has_key("ip_allocations"):
            alloc = json.loads(body_parsed['ip_allocations'])
            self.ank_accessor.ip_allocation = alloc
            self.update_listeners("ip_allocations")
        elif "path" in body_parsed:
            self.notify_listeners(data) # could do extra processing here
        else:
            self.notify_listeners(data)

        for listener in self.event_listeners:
            try:
                listener.write_message(data) 
            except AttributeError:
                pass # listener was removed from parent EchoServer, but not from this stream...?
        logging.info('client quit %s', self.address)
        self.stream_set.remove(self.stream)

    
    def update_listeners(self, index):
        for listener in self.event_listeners:
            if index == "overlays":
                listener.update_overlay()
            elif index == "ip_allocations":
                listener.update_ip_allocation()
            #listener.write_message(body)

class MyWebHandler(tornado.web.RequestHandler):

    def initialize(self, ank_accessor):
        self.ank_accessor = ank_accessor
    
    def get(self):
        self.write("Hello, world")

    def post(self):
        data = self.get_argument('body', 'No data received')
        #self.write(data)
        try:
            body_parsed = json.loads(data)
        except ValueError:
            print "Unable to parse JSON for ", data
            return

        if body_parsed.has_key("anm"):
            print "Received updated network topology"
            if False: # use to save the default.json
                with open(os.path.join(www_dir, "default.json"), "w") as fh:
                    json.dump(body_parsed['anm'], fh)
            self.anm = data
            try:
                self.ank_accessor.anm = body_parsed['anm']
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners("overlays")
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e
        elif body_parsed.has_key("ip_allocations"):
            alloc = json.loads(body_parsed['ip_allocations'])
            self.ank_accessor.ip_allocation = alloc
            self.update_listeners("ip_allocations")
        elif "path" in body_parsed:
            self.update_listeners(data) # could do extra processing here
        else:
            self.update_listeners(data)

        for listener in self.application.socket_listeners:
            listener.write_message(data) 

    def update_listeners(self, index):
        for listener in self.application.socket_listeners:
            if index == "overlays":
                listener.update_overlay()
            elif index == "ip_allocations":
                listener.update_ip_allocation()

    
class OverlayHandler(tornado.web.RequestHandler):
    def initialize(self, ank_accessor):
        self.ank_accessor = ank_accessor

    def get(self):
        overlay_id = self.get_argument("id")
        if overlay_id == "*":
            overlay_list = sorted(self.ank_accessor.overlays())
            self.write(json.dumps({'overlay_list': overlay_list}))
            return

class MyWebSocketHandler(websocket.WebSocketHandler):
    def initialize(self, ank_accessor, overlay_id):
        """ Store the overlay_id this listener is currently viewing.
        Used when updating."""
        self.ank_accessor = ank_accessor
        self.overlay_id = overlay_id

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def open(self, *args, **kwargs):
        print "New client connected"
        self.application.socket_listeners.add(self) 

        try:
            self.application.echo_server.add_event_listener(self)
        except AttributeError:
            pass # no echo server
        try:
            self.application.pc.add_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server
        #pika.log.info("WebSocket opened")

    def on_close(self):
        #pika.log.info("WebSocket closed")
        self.application.socket_listeners.remove(self) 
        try:
            self.application.pc.remove_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server
        try:
            self.application.echo_server.remove_event_listener(self)
        except AttributeError:
            pass # no echo_server

    def on_message(self, message):
        #TODO: look if can map request type here... - or even from the application ws/ mapping
        #self.application.pc.send_message(message) # TODO: do we need to pass it on to rmq?
        if "overlay_id" in message:
            _, overlay_id = message.split("=") #TODO: form JSON on client side, use loads here
            self.overlay_id = overlay_id
            self.update_overlay()
        elif "overlay_list" in message:
            body = json.dumps({'overlay_list': self.ank_accessor.overlays()})
            self.write_message(body)
        elif "ip_allocations" in message:
            body = json.dumps({'ip_allocations': self.ank_accessor.ip_allocations()})
            self.write_message(body)

    def update_overlay(self):
        body = self.ank_accessor[self.overlay_id]
        self.write_message(body)
# and update overlay dropdown
        body = json.dumps({'overlay_list': self.ank_accessor.overlays()})
        self.write_message(body)
#TODO: tidy up the passing of IP allocations

    def update_ip_allocation(self):
        body = json.dumps({'ip_allocations': self.ank_accessor.ip_allocations()})
        self.write_message(body)

class PikaClient(object):
    def __init__(self, io_loop, ank_accessor, host_address):
        #pika.log.info('PikaClient: __init__')
        self.io_loop = io_loop
        self.connected = False
        self.connecting = False
        self.connection = None
        self.channel = None
        self.event_listeners = set([])
        self.queue_name = 'webserver-%i' % os.getpid()
        self.ank_accessor = ank_accessor
        self.host_address = host_address
 
    def connect(self):
        if self.connecting:
            #pika.log.info('PikaClient: Already connecting to RabbitMQ')
            return
 
        #pika.log.info('PikaClient: Connecting to RabbitMQ')
        self.connecting = True
 
        #cred = pika.PlainCredentials('guest', 'guest')
        param = pika.ConnectionParameters(
            host= self.host_address,
            #port=5672,
            #virtual_host='/',
            #credentials=cred
        )
 
        try:
            self.connection = TornadoConnection(param,
                    on_open_callback=self.on_connected)
            self.connection.add_on_close_callback(self.on_closed)
        except pika.exceptions.AMQPConnectionError:
            print("Unable to connect to RabbitMQ")
 
    def on_connected(self, connection):
        #pika.log.info('PikaClient: connected to RabbitMQ')
        self.connected = True
        self.connection = connection
        self.connection.channel(self.on_channel_open)
 
    def on_channel_open(self, channel):
        #pika.log.info('PikaClient: Channel open, Declaring exchange')

        self.channel = channel
        self.channel.exchange_declare(exchange='www',
                                      type="direct",
                                      callback=self.on_exchange_declared)

        return

    def on_exchange_declared(self, frame):
        #pika.log.info('PikaClient: Exchange Declared, Declaring Queue')
        self.channel.queue_declare(queue=self.queue_name,
                                   auto_delete=True,
                                   durable=False,
                                   exclusive=False,
                                   callback=self.on_queue_declared)
        return

    def on_queue_declared(self, frame):
        #pika.log.info('PikaClient: Queue Declared, Binding Queue')
        self.channel.queue_bind(exchange='www',
                                queue=self.queue_name,
                                routing_key='client',
                                callback=self.on_queue_bound)

    def on_queue_bound(self, frame):
        #pika.log.info('PikaClient: Queue Bound, Issuing Basic Consume')
        self.channel.basic_consume(consumer_callback=self.on_message,
                                   queue=self.queue_name,
                                   no_ack=True)
 
    def on_closed(self, connection):
        #pika.log.info('PikaClient: rabbit connection closed')
        self.io_loop.stop()
 
    def on_message(self, channel, method, header, body):
        #pika.log.info('PikaClient: message received: %s' % body)
        import zlib
        try:
            body = zlib.decompress(body)
        except zlib.error:
            pass # likely not compressed body
        body_parsed = json.loads(body)
        if body_parsed.has_key("anm"):
            print "Received updated network topology"
            try:
                self.ank_accessor.anm = body_parsed['anm']
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners("overlays")
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e
        elif body_parsed.has_key("ip_allocations"):
            alloc = json.loads(body_parsed['ip_allocations'])
            self.ank_accessor.ip_allocation = alloc
            self.update_listeners("ip_allocations")
        elif "path" in body_parsed:
            self.notify_listeners(body) # could do extra processing here
        else:
            self.notify_listeners(body)

    def send_message(self, body):
        self.channel.basic_publish(exchange='www',
                      routing_key='server',
                      body=body)
 
    def notify_listeners(self, body):
        for listener in self.event_listeners:
            listener.write_message(body)
            #pika.log.info('PikaClient: notified %s' % repr(listener))

    def update_listeners(self, index):
        for listener in self.event_listeners:
            if index == "overlays":
                listener.update_overlay()
            elif index == "ip_allocations":
                listener.update_ip_allocation()
            #listener.write_message(body)

    def add_event_listener(self, listener):
        self.event_listeners.add(listener)
        #pika.log.info('PikaClient: listener %s added' % repr(listener))
 
    def remove_event_listener(self, listener):
        try:
            self.event_listeners.remove(listener)
            #pika.log.info('PikaClient: listener %s removed' % repr(listener))
        except KeyError:
            pass

class AnkAccessor():
    """ Used to store published topologies"""
    def __init__(self):
        self.anm = {}
        self.ip_allocation = {}
# try loading from vis directory
        try:
            fh = open(os.path.join(www_dir, "default.json"), "r")
            data = json.load(fh)
            #data = json.loads(loaded)
            self.anm = data
        except IOError, e:
            print e
            pass # use default blank anm

    def overlays(self):
        if not len(self.anm):
            return [""]
        return sorted(self.anm.keys())

    def __getitem__(self, key):
        try:
            return self.anm[key]
        except KeyError:
            return json.dumps(["No ANM loaded"])

    def ip_allocations(self):
        return self.ip_allocation
 
def main():
    ank_accessor = AnkAccessor()
# check if most recent outdates current most recent

    settings = {
            "static_path": www_dir,
            'debug': False,
            }


    application = tornado.web.Application([
        (r'/ws', MyWebSocketHandler, {"ank_accessor": ank_accessor, "overlay_id": "phy"}),
        (r'/publish', MyWebHandler, {"ank_accessor": ank_accessor}),
        (r'/overlay', OverlayHandler, {'ank_accessor': ank_accessor}),
        ("/(.*)", tornado.web.StaticFileHandler, {"path":settings['static_path'], "default_filename":"index.html"} )
        ], **settings)

    application.socket_listeners = set() # TODO: see if tornado provides access to listeners

    #pika.log.setup(pika.log.WARNING, color=True)
    io_loop = tornado.ioloop.IOLoop.instance()
    # PikaClient is our rabbitmq consumer
    use_rabbitmq = ank_config.settings['Rabbitmq']['active']
    use_rabbitmq = True
    try:
        import pika
    except ImportError:
        use_rabbitmq = False # don't use pika
    if use_rabbitmq:
        host_address = ank_config.settings['Rabbitmq']['server']
        pc = PikaClient(io_loop, ank_accessor, host_address)
        application.pc = pc
        application.pc.connect()
    else:
        #print "RabbitMQ disabled, exiting. Please set in config."
        pass
        #raise SystemExit

    use_message_pipe = ank_config.settings['Message Pipe']['active']
    #use_message_pipe = False # disable for now
    if use_message_pipe:
        port = ank_config.settings['Message Pipe']['port']
        application.echo_server = EchoServer(ank_accessor = ank_accessor)
        application.echo_server.listen(port)


    #listening for web clientshost_address
#TODO: make this driven from config
    try:
        port = sys.argv[1]
    except IndexError:
        port = 8000
    application.listen(port)

    print "Visualisation server started"
    io_loop.start()

    #TODO: run main web server here too for HTTP

if __name__ == '__main__':
    main()

