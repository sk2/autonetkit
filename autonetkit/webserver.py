# based on http://reminiscential.wordpress.com/2012/04/07/realtime-notification-delivery-using-rabbitmq-tornado-and-websocket/
import tornado
import tornado.websocket as websocket
import os
import json
import logging
import pkg_resources
import socket
www_dir = pkg_resources.resource_filename(__name__, "www_vis")

class MyWebHandler(tornado.web.RequestHandler):

    def initialize(self, ank_accessor, singleuser_mode = False):
        self.ank_accessor = ank_accessor
        self.singleuser_mode = singleuser_mode

    def get(self):
        self.write("Hello, world")

    def post(self):
        data = self.get_argument('body', 'No data received')
        data_type = self.get_argument('type', 'No data received')
        if self.singleuser_mode:
            uuid = "singleuser"
        else:
            uuid = self.get_argument('uuid', 'singleuser')

        # get listeners for this uuid
        uuid_socket_listeners = self.application.socket_listeners[uuid]

        #print "Received data of type %s" % data_type

        if data_type == "anm":
            body_parsed = json.loads(data)

            #TODO: if single user mode then fall back to single user

            if False: # use to save the default.json
                import gzip
                with gzip.open(os.path.join(www_dir, "default.json.gz"), "w") as fh:
                    json.dump(body_parsed, fh)

            self.ank_accessor.store_overlay(uuid, body_parsed)
            #print "Updating listeners for uuid", uuid
            print "Updating listeners"
            for listener in uuid_socket_listeners:
                #print("Updating listener %s for uuid %s" % (listener.request.remote_ip, uuid))
                listener.update_overlay()

        elif data_type == "starting_host":
            for listener in uuid_socket_listeners:
                #TODO: use a json format of {'type': type, 'data': data} in client-side script
                listener.write_message({'starting': data})

        elif data_type == "lab started":
            for listener in uuid_socket_listeners:
                listener.write_message({'lab started': data})

        elif data_type == "highlight":
            body_parsed = json.loads(data)
            for listener in uuid_socket_listeners:
                listener.write_message({'highlight': body_parsed})
        else:
            #print "Received unknown data type %s" % data_type
            pass

class MyWebSocketHandler(websocket.WebSocketHandler):
    def initialize(self, ank_accessor, overlay_id, singleuser_mode = False):
        """ Store the overlay_id this listener is currently viewing.
        Used when updating."""
        self.ank_accessor = ank_accessor
        self.overlay_id = overlay_id
        self.uuid = None # set by the client
        self.uuid_socket_listeners = set()
        self.singleuser_mode = singleuser_mode

    def allow_draft76(self):
        # for iOS 5.0 Safari
        return True

    def open(self, *args, **kwargs):
        # Tornado needs default (here is None) or throws exception that required argument not provided
        if self.singleuser_mode:
            uuid = "singleuser"
        else:
            uuid = self.get_argument("uuid", "singleuser")

        self.uuid = uuid

        self.uuid_socket_listeners = self.application.socket_listeners[uuid]

        #print "Client connected from %s, with uuid %s" % (self.request.remote_ip, uuid)
        print "Client connected from %s" % self.request.remote_ip
        self.uuid_socket_listeners.add(self)

    def on_close(self):
        self.uuid_socket_listeners.remove(self)
        #print "Client disconnected from %s" % self.request.remote_ip
        try:
            self.application.pc.remove_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server
        try:
            self.application.echo_server.remove_event_listener(self)
        except AttributeError:
            pass # no echo_server

    def on_message(self, message):
        #print "Received message %s from client with uuid %s" % (message, self.uuid)
        print "Received message %s from websocket client" % message
        if "overlay_id" in message:
            _, overlay_id = message.split("=") #TODO: form JSON on client side, use loads here
            self.overlay_id = overlay_id
            self.update_overlay()
        elif "overlay_list" in message:
            body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
            self.write_message(body)
        elif "ip_allocations" in message:
            #print "IP Allocations currently unsupported"
            pass

    def update_overlay(self):
        body = self.ank_accessor.get_overlay(self.uuid, self.overlay_id)
        self.write_message(body)
        body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
        self.write_message(body)

class AnkAccessor():
    """ Used to store published topologies"""
    def __init__(self, maxlen = 25):
        from collections import deque
        self.anm_index = {}
        self.uuid_list = deque(maxlen = maxlen)  # use for circular buffer
        self.anm = {}
        self.ip_allocation = {}
# try loading from vis directory
        try:
            import autonetkit_cisco_webui
            default_file = pkg_resources.resource_filename("autonetkit_cisco_webui", "cisco.json.gz")
        except ImportError:
            default_file = os.path.join(www_dir, "default.json.gz")

        try:
            import gzip
            fh = gzip.open(default_file, "r")
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
            logging.debug("Removing uuid %s" % oldest_uuid)

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
                if overlay_id == "*":
                    return anm
                else:
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

    try:
        ANK_VERSION = pkg_resources.get_distribution("autonetkit").version
    except pkg_resources.DistributionNotFound:
        ANK_VERSION = "dev"

    import argparse
    usage = "ank_webserver"
    version = "%(prog)s using AutoNetkit " + str(ANK_VERSION)
    parser = argparse.ArgumentParser(description=usage, version=version)
    parser.add_argument('--port', type=int, default = 8000, help="Port to run webserver on (default 8000)")
    parser.add_argument('--multi_user', action="store_true", default=False, help="Multi-User mode")
    parser.add_argument('--ank_vis', action="store_true", default=False, help="Force AutoNetkit visualisation system")
    arguments = parser.parse_args()

    ank_accessor = AnkAccessor()
# check if most recent outdates current most recent

    content_path = www_dir # default content directory

    #arguments.ank_vis = False # manually force for now

    if not arguments.ank_vis:
        try:
            import autonetkit_cisco_webui
        except ImportError:
            pass  # use AutoNetkit internal web content
        else:
            # use web content from autonetkit_cisco module
            content_path = pkg_resources.resource_filename("autonetkit_cisco_webui", "web_content")

    settings = {
            "static_path": content_path,
            'debug': False,
            "static_url_prefix": "unused", # otherwise content with folder /static won't get mapped
            }

    singleuser_mode = False # default for now
    if arguments.multi_user:
        singleuser_mode = False

    if singleuser_mode:
        print "Running webserver in single-user mode"

    application = tornado.web.Application([
        (r'/ws', MyWebSocketHandler, {"ank_accessor": ank_accessor,
            'singleuser_mode': singleuser_mode,
            "overlay_id": "phy"}),
        (r'/publish', MyWebHandler, {"ank_accessor": ank_accessor,
            'singleuser_mode': singleuser_mode,
            }),
        #TODO: merge the two below into a single handler that captures both cases
        (r'/', IndexHandler, {"path":settings['static_path']}),
        (r'/index.html', IndexHandler, {"path":settings['static_path']}),
        ("/(.*)", tornado.web.StaticFileHandler, {"path":settings['static_path']} )
        ], **settings)


    from collections import defaultdict
    application.socket_listeners = defaultdict(set) # Indexed by uuid

    io_loop = tornado.ioloop.IOLoop.instance()

    port = arguments.port
    try:
        application.listen(port)
    except socket.error, e:
        if e.errno is 48: # socket in use
            logging.warning("Unable to start webserver: socket in use for port %s" % port)
            raise SystemExit

    io_loop.start()

if __name__ == '__main__':
    main()
