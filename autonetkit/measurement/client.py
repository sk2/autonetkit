import zmq
import sys
import random
import time
import json

port = "5559"



#print "Connecting to server..."
#socket = context.socket(zmq.REQ)
#socket.connect ("tcp://54.252.148.199:%s" % port)
#socket = context.socket(zmq.REQ)
#socket.connect ("tcp://localhost:%s" % port)


import Queue
from threading import Thread
source = [
     {'host': "172.16.0.3",   'username': "root", "password": "1234", "command": "ls -lah", },
     {'host': "172.16.0.3",   'username': "root", "password": "1234", "command": "ls -lah", },
     {'host': "172.16.0.3",   'username': "root", "password": "1234", "command": "uname", },
     {'host': "172.16.0.4",   'username': "root", "password": "1234", "command": "ls -lah", },
     {'host': "172.16.0.3",   'username': "root", "password": "1234", "command": "ls -lah", },
     ]

def do_work(socket, data):
    message = json.dumps(data)
    socket.send (message)
    print "waiting for response for %s" % message
    message = socket.recv()
    data = json.loads(message)
    print data
    return str(data)

results_queue = Queue.Queue()

#TODO: check why can't ctrl+c
def worker(socket):
    while True:
        try:
            item = q.get(timeout=1)
        except Queue.Empty:
            return
        result = do_work(socket, item)
        results_queue.put([item, result])
        q.task_done()

q = Queue.Queue()
num_worker_threads = 3
for i in range(num_worker_threads):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect ("tcp://54.252.148.199:%s" % port)
    kwargs = {'socket': socket}
    t = Thread(target=worker, kwargs=kwargs)
    t.daemon = True
    t.start()

for item in source:
    q.put(item)

q.join()

print "DONE"

# now read off results queue
output_results = []
while True:
    try:
        item = results_queue.get(timeout=1)
    except Queue.Empty:
        break
    output_results.append(item)

import pprint
pprint.pprint(output_results)

raise SystemExit


