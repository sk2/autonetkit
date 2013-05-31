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
        uuid = self.get_argument('uuid', 'singleuser')
        print "Received data of type %s" % data_type

        if data_type == "anm":
            body_parsed = json.loads(data)

            #TODO: if single user mode then fall back to single user

            if False: # use to save the default.json
                import gzip
                with gzip.open(os.path.join(www_dir, "default.json.gz"), "w") as fh:
                    json.dump(body_parsed, fh)
            self.anm = data
            try:
                #self.ank_accessor.anm = body_parsed
                self.ank_accessor.store_overlay(uuid, body_parsed)
                #TODO: could process diff and only update client if data has changed -> more efficient client side
                self.update_listeners("overlays")
                # TODO: find better way to replace object not just local reference, as need to replace for RequestHandler too
            except Exception, e:
                print "Exception is", e

        elif data_type == "ip_allocations":
            logging.warning("IP Allocations currently unsupported")
            return
            #body_parsed = json.loads(data)
            #alloc = body_parsed
            #self.ank_accessor.ip_allocation = alloc
            #self.update_listeners("ip_allocations")

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
            #elif index == "ip_allocations":
                #listener.update_ip_allocation()
    
class MyWebSocketHandler(websocket.WebSocketHandler):
    def initialize(self, ank_accessor, overlay_id):
        """ Store the overlay_id this listener is currently viewing.
        Used when updating."""
        self.ank_accessor = ank_accessor
        self.overlay_id = overlay_id
        self.uuid = None # set by the client

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def open(self, *args, **kwargs):
        # Tornado needs default (here is None) or throws exception that required argument not provided
        uuid = self.get_argument("uuid", None) 
        self.uuid = uuid
        print "Client connected from %s, with uuid %s" % (self.request.remote_ip, uuid)
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
        print "received message from client with uuid", self.uuid
        if "overlay_id" in message:
            _, overlay_id = message.split("=") #TODO: form JSON on client side, use loads here
            self.overlay_id = overlay_id
            self.update_overlay()
        elif "overlay_list" in message:
            body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
            self.write_message(body)
        elif "ip_allocations" in message:
            print "IP Allocations currently unsupported"
            #body = json.dumps({'ip_allocations': self.ank_accessor.ip_allocations()})
            #self.write_message(body)

    def update_overlay(self):
        body = self.ank_accessor.get_overlay(self.uuid, self.overlay_id)
        self.write_message(body)
# and update overlay dropdown
        body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
        self.write_message(body)
#TODO: tidy up the passing of IP allocations

    #def update_ip_allocation(self):
        #body = json.dumps({'ip_allocations': self.ank_accessor.ip_allocations()})
        #self.write_message(body)

class AnkAccessor():
    """ Used to store published topologies"""
    def __init__(self, maxlen = 5):
        from collections import deque
        self.anm_index = {}
        self.uuid_list = deque(maxlen = maxlen)  # use for circular buffer
        self.anm = {}
        self.ip_allocation = {}
# try loading from vis directory
        try:
            import gzip
            fh = gzip.open(os.path.join(www_dir, "default.json.gz"), "r")
            data = json.load(fh)
            #data = json.loads(loaded)
            self.anm_index['singleuser'] = data
        except IOError, e:
            print e
            pass # use default blank anm

    def store_overlay(self, uuid, overlay):
        print "Storing overlay with uuid %s" % uuid

        # Check if new uuid or updating previous uuid
        if uuid in self.anm_index:
            self.anm_index[uuid] = overlay
            return

        # New uuid
        if len(self.uuid_list) == self.uuid_list.maxlen:
            # list is full
            oldest_uuid = self.uuid_list.popleft()
            # remove this from anm_inde
            print "removing uuid", oldest_uuid
            print oldest_uuid in self.anm_index.keys()
            del self.anm_index[oldest_uuid] 

        self.uuid_list.append(uuid)
        self.anm_index[uuid] = overlay

    def get_overlay(self, uuid, overlay_id):
        logging.debug("Getting overlay %s with uuid %s" % (overlay_id, uuid))
        try:
            anm = self.anm_index[uuid]
        except KeyError:
            print "Unable to find topology with uuid %s" % uuid
            return ""
        else:
            try:
                return anm[overlay_id]
            except KeyError:
                print "Unable to find overlay %s in topoplogy with uuid %s" % (overlay_id, uuid)

    def overlay_list(self, uuid):
        logging.debug("Trying for anm list with uuid %s" % uuid)
        try:
            anm = self.anm_index[uuid]
        except KeyError:
            print "Unable to find topology with uuid %s" % uuid
            return [""]

        if not len(anm):
            return [""]

        return sorted(anm.keys())

    def __getitem__(self, key):
        try:
            return self.anm[key]
        except KeyError:
            return json.dumps(["No ANM loaded"])

    def ip_allocations(self):
        return self.ip_allocation

class IndexHandler(tornado.web.RequestHandler):
    """Used to treat index.html as a template and substitute the uuid parameter for the websocket call
    """

    def initialize(self, path):
        self.content_path = path

    def get(self):
        # if not set, use default uuid of "singleuser"
        uuid = self.get_argument("uuid", "singleuser") 
        logging.info("Rendering template with uuid %s" % uuid)
        template = os.path.join(self.content_path, "index.html")
        self.render(template, uuid = uuid)
 
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
            "static_url_prefix": "unused", # otherwise content with folder /static won't get mapped
            }

    application = tornado.web.Application([
        (r'/ws', MyWebSocketHandler, {"ank_accessor": ank_accessor, "overlay_id": "phy"}),
        (r'/publish', MyWebHandler, {"ank_accessor": ank_accessor}),
        #TODO: merge the two below into a single handler that captures both cases
        (r'/', IndexHandler, {"path":settings['static_path']}),
        (r'/index.html', IndexHandler, {"path":settings['static_path']}),
        ("/(.*)", tornado.web.StaticFileHandler, {"path":settings['static_path']} )
        ], **settings)


    from collections import defaultdict
    application.socket_listeners = defaultdict(set) # Indexed by uuid

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

