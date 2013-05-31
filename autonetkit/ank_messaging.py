import autonetkit.config as config
import autonetkit.log as log
import socket
import autonetkit.ank_json

use_rabbitmq = config.settings['Rabbitmq']['active']
if use_rabbitmq:
    import pika

use_http_post = config.settings['Http Post']['active']
if use_http_post:
    import urllib

def format_http_url(settings):
    host = settings['Http Post']['server']
    port = settings['Http Post']['port']
    return "http://%s:%s/publish" % (host, port)

http_url = format_http_url(config.settings)

def update_http(anm = None, nidb = None):

    if anm and nidb:
        body = autonetkit.ank_json.dumps(anm, nidb)
    elif anm:
        body = autonetkit.ank_json.dumps(anm)
    else:
        import json
        body = json.dumps({}) # blank to test visualisation server running

    uuid = get_uuid(anm)

    params = urllib.urlencode({
        'body': body,
        'type': 'anm',
        'uuid': uuid,
        })
    try:
        data = urllib.urlopen(http_url, params).read()
    except IOError, e:
        log.info("Unable to connect to visualisation server %s" % http_url)
        return

    if not anm:
        # testing
        log.info("Visualisation server running")

def get_uuid(anm):
    try:
        return anm['phy'].data['uuid']
    except KeyError:
        log.warning("UUID not set, returning singleuser uuid")
        return "singleuser"


def highlight(nodes, edges, paths = None, uuid = "singleuser"):
    if not paths:
        paths = []

    def nfilter(n):
        try:
            return n.id
        except AttributeError:
            return n # likely already a node id (string)

    def efilter(e):
        try:
            return (e.src.id, e.dst.id)
        except AttributeError:
            return e # likely already edge (src, dst) id tuple (string)

    nodes = [nfilter(n) for n in nodes]
    edges = [efilter(e) for e in edges]
    filtered_paths = []
    for path in paths:
        #TODO: tidy this logic
        if isinstance(path, dict) and 'path' in path:
            path_data = path # use as-s
        else:
            import random
            is_verified = bool(random.randint(0,1))
            path_data = {'path': path,
                    'verified': is_verified}

        path_data['path'] = [nfilter(n) for n in path_data['path']]
        filtered_paths.append(path_data)

    #TODO: remove "highlight" from json, use as url params to distinguish
    import json
    body = json.dumps({
        'nodes': nodes,
        'edges': edges,
        'paths': filtered_paths,
        })

    params = urllib.urlencode({
        'body': body,
        'type': 'highlight',
        'uuid': uuid,
        })

    #TODO: split this common function out, create at runtime so don't need to keep reading config
    try:
        data = urllib.urlopen(http_url, params).read()
    except IOError, e:
        log.info("Unable to connect to HTTP Server %s: %s" % (http_url, e))

def publish_data(data, type_key):
    params = urllib.urlencode({
        'body': data,
        'type': type_key,
        })

    #TODO: split this common function out, create at runtime so don't need to keep reading config
    try:
        data = urllib.urlopen(http_url, params).read()
    except IOError, e:
        log.info("Unable to connect to HTTP Server %s: %s" % (http_url, e))

class AnkMessaging(object):

    def __init__(self, host = None):
        try:
            if use_rabbitmq:
                log.debug("Using Rabbitmq with server %s " % host)
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host = host))
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange='www',
                        type='direct')
                self.publish = self.publish_pika
                self.publish_compressed = self.publish_compressed_pika

            if use_http_post:
                host = config.settings['Http Post']['server']
                port = config.settings['Http Post']['port']
                self.http_url = "http://%s:%s/publish" % (host, port)
                self.publish = self.publish_http_post
                self.publish_compressed = self.publish_http_post

            if not (use_rabbitmq or use_http_post):
                log.debug("Not using Rabbitmq or telnet")
                self.publish = self.publish_blank_stub
                self.publish_compressed = self.publish_blank_stub
        except socket.timeout: #TODO: check if these should move up to the use_rabbitmq block
            log.warning("Socket Timeout: not using Rabbitmq")
            self.publish = self.publish_blank_stub
            self.publish_compressed = self.publish_blank_stub
        except socket.error:
            log.warning("Socket Error: not using Rabbitmq")
            self.publish = self.publish_blank_stub
            self.publish_compressed = self.publish_blank_stub
    
    def publish(self):
        pass # will be replaced at init

    def publish_compressed(self):
        pass # will be replaced at init

    def publish_anm(self, anm, nidb = None):
        """JSON-ifies the anm and sends it"""
        if nidb:
            body = autonetkit.ank_json.dumps(anm, nidb)
        else:
            body = autonetkit.ank_json.dumps(anm)
        self.publish_compressed("www", "client", body)

    def publish_json(self, body):
        import json
        data = json.dumps(body, cls=autonetkit.ank_json.AnkEncoder, indent = 4)
        self.publish(None, None, data)

    def publish_compressed_telnet(self, exchange, routing_key, body):
        import zlib
#TODO: note don't compress - no upper bound if telnet sockets
        #body = zlib.compress(body, 9)
        self.tn.write(body + "__end__")

    def publish_pika(self, exchange, routing_key, body):
        self.channel.basic_publish(exchange= exchange,
                routing_key = routing_key,
                body= body)

    def publish_compressed_pika(self, exchange, routing_key, body):
        """Compresses body using zlib before sending"""
        import zlib
        body = zlib.compress(body, 9)
        self.publish(exchange, routing_key, body)

        #TODO: implement callback
    def publish_blank_stub(self, exchange, routing_key, body):
        """use if not using rabbitmq, simplifies calls elsewhere (publish does nothing)"""
#TODO: log that not sending for debug purposes
        return

    def publish_http_post(self, exchange, routing_key, body):
        print "called"
        params = urllib.urlencode({
            'body': body
            })
        try:
            data = urllib.urlopen(self.http_url, params).read()
        except IOError, e:
            log.info("Unable to connect to HTTP Server %s" % self.http_url)

        #print data # can log response

#TODO: write new module that sends to webserver and takes parameter to distinguish eg starting, ip_allocations, etc
