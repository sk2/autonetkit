import time
import zmq
import pprint

def result_collector():
    context = zmq.Context()
    results_receiver = context.socket(zmq.PULL)
    results_receiver.bind("tcp://127.0.0.1:5558")
    collecter_data = {}
    for x in xrange(1000):
        result = results_receiver.recv_json()
        print result


result_collector()

raise SystemExit


import zmq
# from https://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/devices/queue.html

def main():

    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.ROUTER)
        frontend.bind("tcp://*:5559")
        # Socket facing services
        backend = context.socket(zmq.DEALER)
        backend.bind("tcp://*:5560")

        zmq.device(zmq.QUEUE, frontend, backend)
    except Exception, e:
        print e
        print "bringing down zmq device"
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    main(   )