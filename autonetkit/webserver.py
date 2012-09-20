# based on http://reminiscential.wordpress.com/2012/04/07/realtime-notification-delivery-using-rabbitmq-tornado-and-websocket/
import pika
import tornado
import tornado.websocket as websocket
from pika.adapters.tornado_connection import TornadoConnection
import os
import json
import glob
import sys
import autonetkit.config

class MyWebHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class OverlayHandler(tornado.web.RequestHandler):
    def initialize(self, anm):
        self.anm = anm

    def get(self):
        overlay_id = self.get_argument("id")
        if overlay_id == "*":
            overlay_list = sorted(self.anm.overlays())
            self.write(json.dumps({'overlay_list': overlay_list}))
            return

class MyWebSocketHandler(websocket.WebSocketHandler):
    def initialize(self, anm, overlay_id):
        """ Store the overlay_id this listener is currently viewing.
        Used when updating."""
        self.anm = anm
        self.overlay_id = overlay_id

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def open(self, *args, **kwargs):
        self.application.pc.add_event_listener(self)
        pika.log.info("WebSocket opened")

    def on_close(self):
        pika.log.info("WebSocket closed")
        self.application.pc.remove_event_listener(self)

    def on_message(self, message):
        #TODO: look if can map request type here... - or even from the application ws/ mapping
        #self.application.pc.send_message(message) # TODO: do we need to pass it on to rmq?
        if "overlay_id" in message:
            _, overlay_id = message.split("=") #TODO: form JSON on client side, use loads here
            self.overlay_id = overlay_id
            self.update_overlay()
        elif "overlay_list" in message:
            body = json.dumps({'overlay_list': self.anm.overlays()})
            self.write_message(body)

    def update_overlay(self):
        body = self.anm[self.overlay_id]
        self.write_message(body)
# and update overlay dropdown
        body = json.dumps({'overlay_list': self.anm.overlays()})
        self.write_message(body)
        

class PikaClient(object):
    def __init__(self, io_loop, anm):
        pika.log.info('PikaClient: __init__')
        self.io_loop = io_loop
        self.connected = False
        self.connecting = False
        self.connection = None
        self.channel = None
        self.event_listeners = set([])
        self.queue_name = 'webserver-%i' % os.getpid()
        self.anm = anm
 
    def connect(self):
        if self.connecting:
            pika.log.info('PikaClient: Already connecting to RabbitMQ')
            return

 
        pika.log.info('PikaClient: Connecting to RabbitMQ')
        self.connecting = True
 
        #cred = pika.PlainCredentials('guest', 'guest')
        host = autonetkit.config.settings['Rabbitmq']['server']
        param = pika.ConnectionParameters(
            host= host,
            #port=5672,
            #virtual_host='/',
            #credentials=cred
        )
 
        self.connection = TornadoConnection(param,
            on_open_callback=self.on_connected)
        self.connection.add_on_close_callback(self.on_closed)
 
    def on_connected(self, connection):
        pika.log.info('PikaClient: connected to RabbitMQ')
        self.connected = True
        self.connection = connection
        self.connection.channel(self.on_channel_open)
 
    def on_channel_open(self, channel):
        pika.log.info('PikaClient: Channel open, Declaring exchange')

        self.channel = channel
        self.channel.exchange_declare(exchange='www',
                                      type="direct",
                                      callback=self.on_exchange_declared)

        return

    def on_exchange_declared(self, frame):
        pika.log.info('PikaClient: Exchange Declared, Declaring Queue')
        self.channel.queue_declare(queue=self.queue_name,
                                   auto_delete=True,
                                   durable=False,
                                   exclusive=False,
                                   callback=self.on_queue_declared)
        return

    def on_queue_declared(self, frame):
        pika.log.info('PikaClient: Queue Declared, Binding Queue')
        self.channel.queue_bind(exchange='www',
                                queue=self.queue_name,
                                routing_key='client',
                                callback=self.on_queue_bound)

    def on_queue_bound(self, frame):
        pika.log.info('PikaClient: Queue Bound, Issuing Basic Consume')
        self.channel.basic_consume(consumer_callback=self.on_message,
                                   queue=self.queue_name,
                                   no_ack=True)
 
    def on_closed(self, connection):
        pika.log.info('PikaClient: rabbit connection closed')
        self.io_loop.stop()
 
    def on_message(self, channel, method, header, body):
        pika.log.info('PikaClient: message received: %s' % body)
        import zlib
        try:
            body = zlib.decompress(body)
        except zlib.error:
            pass # likely not compressed body
        body_parsed = json.loads(body)
        if body_parsed.has_key("anm"):
            print "received new anm"
            try:
                self.anm.anm = body_parsed['anm']
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners()
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e
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
            pika.log.info('PikaClient: notified %s' % repr(listener))

    def update_listeners(self):
        for listener in self.event_listeners:
            listener.update_overlay()
            #listener.write_message(body)

    def add_event_listener(self, listener):
        self.event_listeners.add(listener)
        pika.log.info('PikaClient: listener %s added' % repr(listener))
 
    def remove_event_listener(self, listener):
        try:
            self.event_listeners.remove(listener)
            pika.log.info('PikaClient: listener %s removed' % repr(listener))
        except KeyError:
            pass


class AnmAccessor():
    def __init__(self):
        self.anm = {}
# try loading from vis directory
        try:
            fh = open("ank_vis/default.json", "r")
            data = json.load(fh)
            #data = json.loads(loaded)
            self.anm = data.get("anm")
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
 
def main():
    # bootstrap: load anm from file
    directory = os.path.join("versions", "anm")
    glob_dir = os.path.join(directory, "*.pickle.tar.gz")
    pickle_files = glob.glob(glob_dir)
    pickle_files = sorted(pickle_files)
    anm = AnmAccessor()
# check if most recent outdates current most recent

    static_path = os.path.join("ank_vis")
    settings = {
            "static_path": static_path,
            'debug': False,
            }

    application = tornado.web.Application([
        (r'/ws', MyWebSocketHandler, {"anm": anm, "overlay_id": "phy"}),
        (r'/overlay', OverlayHandler, {'anm': anm}),
        ("/(.*)", tornado.web.StaticFileHandler, {"path":settings['static_path'], "default_filename":"index.html"} )
        ], **settings)
    pika.log.setup(pika.log.DEBUG, color=True)
    io_loop = tornado.ioloop.IOLoop.instance()
    # PikaClient is our rabbitmq consumer
    pc = PikaClient(io_loop, anm)
    application.pc = pc
    application.pc.connect()
    try:
        port = sys.argv[1]
    except IndexError:
        port = 8000
    application.listen(port)
    io_loop.start()

    #TODO: run main web server here too for HTTP

if __name__ == '__main__':
    main()

