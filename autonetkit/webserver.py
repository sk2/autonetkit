# based on http://reminiscential.wordpress.com/2012/04/07/realtime-notification-delivery-using-rabbitmq-tornado-and-websocket/
import json
import logging
import os
import socket

import autonetkit.config as config
import pkg_resources
import tornado
import tornado.websocket as websocket


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


        if data_type == "anm":
            body_parsed = json.loads(data)

            #TODO: if single user mode then fall back to single user

            if False: # use to save the default.json
                import gzip
                vis_content = pkg_resources.resource_filename("autonetkit_vis", "web_content")
                with gzip.open(os.path.join(vis_content, "default.json.gz"), "w") as fh:
                    json.dump(body_parsed, fh)

            self.ank_accessor.store_overlay(uuid, body_parsed)
            logging.info("Updating listeners")
            for listener in uuid_socket_listeners:
                listener.update_overlay()

        elif data_type == "highlight":
            body_parsed = json.loads(data)
            for listener in uuid_socket_listeners:
                listener.write_message({'highlight': body_parsed})
        else:
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

        logging.info("Client connected from %s" % self.request.remote_ip)
        self.uuid_socket_listeners.add(self)

    def on_close(self):
        self.uuid_socket_listeners.remove(self)
        logging.info("Client disconnected from %s" % self.request.remote_ip)
        try:
            self.application.pc.remove_event_listener(self)
        except AttributeError:
            pass # no RabbitMQ server
        try:
            self.application.echo_server.remove_event_listener(self)
        except AttributeError:
            pass # no echo_server

    def on_message(self, message):
        logging.info("Received message %s from websocket client" % message)
        if "overlay_id" in message:
            _, overlay_id = message.split("=") #TODO: form JSON on client side, use loads here
            self.overlay_id = overlay_id
            self.update_overlay()
        elif "overlay_list" in message:
            body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
            self.write_message(body)
        elif "ip_allocations" in message:
            pass

    def update_overlay(self):
        body = self.ank_accessor.get_overlay(self.uuid, self.overlay_id)
        self.write_message(body)
        body = json.dumps({'overlay_list': self.ank_accessor.overlay_list(self.uuid)})
        self.write_message(body)

class AnkAccessor():
    """ Used to store published topologies"""
    def __init__(self, maxlen = 25, simplified_overlays = False):
        from collections import deque
        self.anm_index = {}
        self.uuid_list = deque(maxlen = maxlen)  # use for circular buffer
        self.anm = {}
        self.ip_allocation = {}
        self.simplified_overlays = simplified_overlays
# try loading from vis directory
        try:
            import autonetkit_cisco_webui
            default_file = pkg_resources.resource_filename("autonetkit_cisco_webui", "cisco.json.gz")
        except ImportError:
            vis_content = pkg_resources.resource_filename("autonetkit_vis", "web_content")
            default_file = os.path.join(vis_content, "default.json.gz")

        try:
            import gzip
            fh = gzip.open(default_file, "r")
            data = json.load(fh)
            #data = json.loads(loaded)
            self.anm_index['singleuser'] = data
        except IOError, e:
            logging.warning(e)
            pass # use default blank anm

    def store_overlay(self, uuid, overlay_input):
        logging.info("Storing overlay_input with UUID %s" % uuid)

        if self.simplified_overlays:
            overlays_tidied = {}

            overlay_keys = [index for index, data in overlay_input.items() if len(data.get("nodes"))]

            keys_to_exclude = {"input", "input_directed",
            "bgp", "ibgp", "ebgp",
            "graphics", "ip", "nidb"}
            overlay_keys = [k for k in overlay_keys if k not in keys_to_exclude]

            labels = {
            "l3_conn": "L3 Connectivity",
            "ibgp_v6": "iBGP v6",
            "ibgp_v4": "iBGP v4",
            "ibgp_vpn_v4": "iBGP VPN v4",
            "ebgp_v6": "eBGP v6",
            "mpls_te": "MPLS TE",
            "mpls_ldp": "MPLS LDP",
            "ebgp_v4": "eBGP v4",
            "mpls_oam": "MPLS OAM",
            "ipv4": "IP v4",
            "ipv6": "IP v6",
            "segment_routing": "Segment Routing",
            "pce": "PCE",
            "bgp_ls": "BGP LS",
            "phy": "Physical",
            "vrf": "VRF",
            "isis": "IS-IS",
            "bgp": "BGP",
            "eigrp": "EIGRP",
            "ebgp": "eBGP",
            "ospf": "OSPF",
            }

            #DIsable until all web engines are verified to support format (eg ank_cisco_webui)
            labels = {}

            # Check if new uuid or updating previous uuid
            for key in overlay_keys:
                store_key = labels.get(key) or key # use from labels if present
                overlays_tidied[store_key] = overlay_input[key]

        else:
            overlays_tidied = overlay_input

        # New uuid
        if len(self.uuid_list) == self.uuid_list.maxlen:
            # list is full
            oldest_uuid = self.uuid_list.popleft()
            logging.info("UUID list full, removing UUID %s" % oldest_uuid)

            try:
                del self.anm_index[oldest_uuid]
            except KeyError:
                logging.warning("Unable to remove UUID %s" % oldest_uuid)

        # If uuid already present, then remove from the queue, and then add to the end
        # This avoids erroneously removing recently updated (i.e. non-stale uuids)
        if uuid in self.uuid_list:
            logging.info("Removing UUID %s to add to end of queue" % uuid)
            self.uuid_list.remove(uuid)

        self.uuid_list.append(uuid)
        logging.info("Stored overlay with UUID %s" % uuid)
        self.anm_index[uuid] = overlays_tidied

    def get_overlay(self, uuid, overlay_id):
        logging.info("Getting overlay %s with UUID %s" % (overlay_id, uuid))
        try:
            anm = self.anm_index[uuid]
        except KeyError:
            logging.warning("Unable to find topology with UUID %s" % uuid)
            return ""
        else:
            try:
                if overlay_id == "*":
                    return anm
                #elif self.simplified_overlays and overlay_id == "phy":
                    #print "Returning physical for phy"
                    #return anm["Physical"]
                else:
                    return anm[overlay_id]
            except KeyError:
                logging.warning("Unable to find overlay %s in topoplogy with UUID %s" % (overlay_id, uuid))

    def overlay_list(self, uuid):
        logging.info("Trying for anm list with UUID %s" % uuid)
        try:
            anm = self.anm_index[uuid]
        except KeyError:
            logging.warning("Unable to find topology with UUID %s" % uuid)
            return [""]

        if not len(anm):
            return [""]

        return sorted(anm.keys(), key = lambda x: str(x[0]).lower())

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
    parser.add_argument('--port', type=int,  help="Port to run webserver on (default 8000)")
    parser.add_argument('--multi_user', action="store_true", default=False, help="Multi-User mode")
    parser.add_argument('--ank_vis', action="store_true", default=False, help="Force AutoNetkit visualisation system")
    arguments = parser.parse_args()

# check if most recent outdates current most recent
    content_path = None

    try:
        import autonetkit_vis
    except ImportError:
        pass  # #TODO: logging no vis
    else:
        # use web content from autonetkit_cisco module
        content_path = pkg_resources.resource_filename("autonetkit_vis", "web_content")

    #arguments.ank_vis = False # manually force for now

    simplified_overlays = False
    if not arguments.ank_vis:
        try:
            import autonetkit_cisco_webui
            simplified_overlays = True
        except ImportError:
            pass  # use AutoNetkit internal web content
        else:
            # use web content from autonetkit_cisco module
            content_path = pkg_resources.resource_filename("autonetkit_cisco_webui", "web_content")

    if not content_path:
        logging.warning("No visualisation pages found: did you mean to install autonetkit_vis? Exiting...")
        raise SystemExit

    settings = {
            "static_path": content_path,
            'debug': False,
            "static_url_prefix": "unused", # otherwise content with folder /static won't get mapped
            }

    singleuser_mode = False # default for now
    if arguments.multi_user:
        singleuser_mode = False

    if singleuser_mode:
        logging.info("Running webserver in single-user mode")

    ank_accessor = AnkAccessor(simplified_overlays = simplified_overlays)

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

    logging.getLogger().setLevel(logging.INFO)


    from collections import defaultdict
    application.socket_listeners = defaultdict(set) # Indexed by uuid

    io_loop = tornado.ioloop.IOLoop.instance()

    port = config.settings['Http Post']['port']
    if arguments.port:
        port = arguments.port #explicitly set on command line

    import time
    timestamp = time.strftime("%Y %m %d_%H:%M:%S", time.localtime())
    logging.info("Starting on port %s at %s" % (port, timestamp))

    try:
        application.listen(port)
    except socket.error, e:
        if e.errno is 48: # socket in use
            logging.warning("Unable to start webserver: socket in use for port %s" % port)
            raise SystemExit

    io_loop.start()

if __name__ == '__main__':
    main()
