"""Zmq based measurement client"""
import zmq
import json
import autonetkit
import pkg_resources
import os
import autonetkit.measurement.process as process
import autonetkit.ank_messaging as ank_messaging
import autonetkit.config as config

server = config.settings['Measurement']['host']
port = config.settings['Measurement']['port']
print server, port

def main():
    import Queue
    from threading import Thread

    nidb = autonetkit.NIDB()
    nidb.restore_latest()
    rev_map = process.build_reverse_mappings_from_nidb(nidb)

    template_file = pkg_resources.resource_filename(__name__, "../textfsm/linux/traceroute")
    template_file = os.path.abspath(template_file)

    commands = []
    import random
    dest_node = random.choice([n for n in nidb.nodes("is_l3device")])
    print "tracing path to ", dest_node
    ank_messaging.highlight(nodes = [dest_node])
    dest_ip = list(dest_node.physical_interfaces)[0].ipv4_address
    cmd = "traceroute -n -a -U -w 1.0 %s" % dest_ip
    #cmd = "traceroute -n -a -U -w 0.5 10.5.0.2"

#TODO: also take port argument (default of 23), and method argument (telnet (default), ssh, ..., etc)

    for node in nidb.routers():
        commands.append({'host': str(node.tap.ip),
         'username': "root", "password": "1234",
         "command": cmd, "template": template_file, "rev_map" : rev_map,
         "source": node, "destination": dest_node,
          })

    def do_work(socket, user_data):
        #TODO: make username and password optional
        #print "Sent", ", ".join(["%s: %s" % (k, v) for k, v in data.items()])
        core_keys = ("host", "username", "password", "command")
        core_data = {k: v for k,v in user_data.items() if k in core_keys}
        print "Sent %s to %s" % (core_data['command'], core_data['host'])
        message = json.dumps(core_data)
        socket.send (message)
        #print "waiting for response for %s" % message
        message = socket.recv()
        result = str(json.loads(message))
        #import q
        #q(result)
        print result

        template = user_data['template']
        rev_map = user_data['rev_map']
        source = user_data['source']
        destination = user_data['destination']
        header, routes = process.process_traceroute(template_file, result)
        path = process.extract_path_from_parsed_traceroute(header, routes)
        hosts = process.reverse_map_path(rev_map, path)
        hosts.insert(0, source)
        #TODO: push processing results onto return values
        print hosts
        # only send if complete path
        if hosts[-1] == destination:
            path_data = {'path': hosts}
            ank_messaging.highlight(paths = [path_data])
        else:
            print "Incomplete path", hosts, destination

        return str(result)

    def process_data(user_data, result):
        # TODO: test if command is traceroute
        template = user_data['template']
        rev_map = user_data['rev_map']
        source = user_data['source']
        destination = user_data['destination']
        header, routes = process.process_traceroute(template_file, result)
        path = process.extract_path_from_parsed_traceroute(header, routes)
        hosts = process.reverse_map_path(rev_map, path)
        hosts.insert(0, source)
        #TODO: push processing results onto return values
        print hosts
        # only send if complete path
        if hosts[-1] == destination:
            path_data = {'path': hosts}
            ank_messaging.highlight(paths = [path_data])
        else:
            print "Incomplete path", hosts, destination

    results_queue = Queue.Queue()

    #TODO: check why can't ctrl+c
    def worker():
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect ("tcp://%s:%s" % (server, port))
        while True:
            try:
                (_, key, item)  = q.get(timeout=1)
            except Queue.Empty:
                return
            if key == "command":
                # only send the core information: not extra info for parsing
                result = do_work(socket, item)
                #q.put((10, "process", (item, result)))
            if key == "process":
                user_data, result = item
                process_data(user_data, result)

            q.task_done()

    q = Queue.PriorityQueue()
    num_worker_threads = 10
    for i in range(num_worker_threads):
        t = Thread(target=worker)
        t.daemon = True
        t.start()

    for item in commands:
        q.put((20, "command", item))

    q.join()

    print "Finished measurement"

    # now read off results queue
    output_results = []
    while True:
        try:
            item = results_queue.get(timeout=1)
        except Queue.Empty:
            break
        output_results.append(item)


if __name__ == "__main__":
    main()
