# based on http://reminiscential.wordpress.com/2012/04/07/realtime-notification-delivery-using-rabbitmq-tornado-and-websocket/
import tornado
import tornado.websocket as websocket
import os
import json
import glob
import sys
import autonetkit.config as ank_config
import logging
import pkg_resources
import socket
www_dir = pkg_resources.resource_filename(__name__, "www_vis")

class MyWebHandler(tornado.web.RequestHandler):

    def initialize(self, ank_accessor):
        self.ank_accessor = ank_accessor
    
    def get(self):
        self.write("Hello, world")

    def post(self):
        data = self.get_argument('body', 'No data received')
        data_type = self.get_argument('type', 'No data received')
        print "Received data of type %s" % data_type
        #self.write(data)

        if data_type == "anm":
            body_parsed = json.loads(data)
            if False: # use to save the default.json
                import gzip
                with gzip.open(os.path.join(www_dir, "default.json.gz"), "w") as fh:
                    json.dump(body_parsed, fh)
            self.anm = data
            try:
                self.ank_accessor.anm = body_parsed
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners("overlays")
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e

        elif data_type == "ip_allocations":
            body_parsed = json.loads(data)
            alloc = body_parsed
            self.ank_accessor.ip_allocation = alloc
            self.update_listeners("ip_allocations")

        elif data_type == "starting_host":
            self.update_listeners(data) 
            for listener in self.application.socket_listeners:
                #TODO: use a json format of {'type': type, 'data': data} in client-side script
                listener.write_message({'starting': data}) 

        elif data_type == "lab started":
            self.update_listeners(data) 
            for listener in self.application.socket_listeners:
                listener.write_message({'lab started': data}) 

        elif data_type == "highlight":
            #self.update_listeners(data) 
            body_parsed = json.loads(data)
            for listener in self.application.socket_listeners:
                #listener.write_message(data) 
                listener.write_message({'highlight': body_parsed}) 
        else:
            self.update_listeners(data)

        #for listener in self.application.socket_listeners:
            #listener.write_message(data) 

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
        print "Client connected from %s" % self.request.remote_ip
        self.application.socket_listeners.add(self) 

        try:
            self.application.pc.add_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server

    def on_close(self):
        self.application.socket_listeners.remove(self) 
        print "Client disconnected from %s" % self.request.remote_ip
        try:
            self.application.pc.remove_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server
        try:
            self.application.echo_server.remove_event_listener(self)
        except AttributeError:
            pass # no echo_server

    def on_message(self, message):
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

class AnkAccessor():
    """ Used to store published topologies"""
    def __init__(self):
        self.anm = {}
        self.ip_allocation = {}
# try loading from vis directory
        try:
            import gzip
            fh = gzip.open(os.path.join(www_dir, "default.json.gz"), "r")
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

    content_path = www_dir # default content directory

    try:
        import autonetkit_cisco
    except ImportError:
        pass  # use AutoNetkit internal web content
    else:
        # use web content from autonetkit_cisco module
        content_path = pkg_resources.resource_filename("autonetkit_cisco", "web_content")

    print content_path
    settings = {
            "static_path": content_path,
            'debug': False,
            "static_url_prefix": "test",
            }

    application = tornado.web.Application([
        (r'/ws', MyWebSocketHandler, {"ank_accessor": ank_accessor, "overlay_id": "phy"}),
        (r'/publish', MyWebHandler, {"ank_accessor": ank_accessor}),
        (r'/overlay', OverlayHandler, {'ank_accessor': ank_accessor}),
        ("/(.*)", tornado.web.StaticFileHandler, {"path":settings['static_path'], "default_filename":"index.html"} )
        ], **settings)


    application.socket_listeners = set() # TODO: see if tornado provides access to listeners

    io_loop = tornado.ioloop.IOLoop.instance()
    # PikaClient is our rabbitmq consumer
  
    #listening for web clientshost_address
#TODO: make this driven from config
    try:
        port = sys.argv[1]
    except IndexError:
        port = 8000
    try:
        application.listen(port)
    except socket.error, e:
        if e.errno is 48: # socket in use
            logging.warning("Unable to start webserver: socket in use for port %s" % port)
            raise SystemExit


    print "Visualisation server started"
    io_loop.start()

if __name__ == '__main__':
    main()

