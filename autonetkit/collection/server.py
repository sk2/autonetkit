"""Zmq based measurement server"""
# based on https://learning-0mq-with-pyzmq.readthedocs.org/en/latest/pyzmq/patterns/pushpull.html


import zmq
import json
import socket as python_socket
import telnetlib
from threading import Thread
import time
import sys


def streamer_device(port_in, port_out):
    from zmq.devices import ProcessDevice

    pd = ProcessDevice(zmq.QUEUE, zmq.PULL, zmq.PUSH)
    pd.bind_in('tcp://*:%s' % port_in)
    pd.bind_out('tcp://*:%s' % port_out)
    pd.setsockopt_in(zmq.IDENTITY, 'PULL')

    pd.setsockopt_out(zmq.IDENTITY, 'PUSH')
    pd.start()
# it will now be running in a background process

def forwarder_device(port_in, port_out):
    from zmq.devices import ProcessDevice

    pd = ProcessDevice(zmq.FORWARDER, zmq.SUB, zmq.PUB)
    pd.bind_in('tcp://*:%s' % port_in)
    pd.bind_out('tcp://*:%s' % port_out)
    pd.setsockopt_in(zmq.IDENTITY, 'SUB')
    pd.setsockopt_in(zmq.SUBSCRIBE, "")
    pd.setsockopt_out(zmq.IDENTITY, 'PUB')
    pd.start()
# it will now be running in a background process

CONNECTORS = {}

#TODO: inherit from base autonetkit connector abstract function
def netkit_connector(host, username, password, command, *args, **kwargs):
    #Note: user prompt and priv prompt have same password
    vtysh = kwargs.get("vtysh", False)

    print host, username, password, command, vtysh

    print "Connecting to %s" % (host)
    try:
        tn = telnetlib.Telnet(host, timeout = 10)
    except Exception, e:
        print "Unable to connect to %s: %s" % (host, e)
        return

    tn.set_debuglevel(0)
    print "Connected to %s" % host

    welcome_banner = tn.read_until("login:", timeout = 10)
    last_line = welcome_banner.splitlines()[-1]
    hostname = last_line.replace("login:", "").strip()

    linux_prompt = hostname + ":~#"

    print "Hostname is %s" % hostname

    #TODO: check why need the below for ascii/unicode/pzmq?

    tn.write(username + '\n')
    tn.read_until("Password:", timeout = 10)
    tn.write(password + '\n')
    tn.read_until(linux_prompt, timeout = 10)
    if vtysh:
        vtysh_prompt = hostname + "#"
        tn.write("vtysh" + "\n")
        tn.read_until(vtysh_prompt, timeout = 10)
        tn.write("terminal length 0" + "\n")
        tn.read_until(vtysh_prompt, timeout = 10)
        tn.write(command + "\n")
        result = tn.read_until(vtysh_prompt, timeout = 10)
        tn.write("exit" + "\n")
        #TODO: check if need to parse result also to strip out prompt
    else:
        tn.write(command + "\n")
        result = tn.read_until(linux_prompt, timeout = 10)
        result = "\n".join(result.splitlines()[1:-1])

    print "Finished for %s" % hostname

    tn.write("exit" + "\n")
    return hostname, result

CONNECTORS['netkit'] = netkit_connector
try:
  import autonetkit_cisco
  import autonetkit_cisco.measure_connectors
except ImportError:
  pass # not installed
else:
  CONNECTORS['ios_classic'] = autonetkit_cisco.measure_connectors.ios_classic_connector
  CONNECTORS['ios_classic_ns'] = autonetkit_cisco.measure_connectors.ios_classic_ns_connector
  CONNECTORS['ios_xr'] = autonetkit_cisco.measure_connectors.ios_xr_connector
  CONNECTORS['ios_xr_ns'] = autonetkit_cisco.measure_connectors.ios_xr_ns_connector
  CONNECTORS['titanium_ns_connector'] = autonetkit_cisco.measure_connectors.titanium_ns_connector

def do_connect(**kwargs):
  #TODO: use a function map
  connector = kwargs.get("connector")
  connector_fn = CONNECTORS[connector] #TODO: capture if not found
  try:
    return connector_fn(**kwargs)
  except EOFError:
    print "Unable to connect with connector %s" % connector
    return ""

def worker():
    context = zmq.Context()
    # recieve work
    consumer_receiver = context.socket(zmq.PULL)
    consumer_receiver.connect("tcp://127.0.0.1:5560")
    # send work
    consumer_sender = context.socket(zmq.PUB)
    consumer_sender.connect("tcp://127.0.0.1:5561")
    while True:
       #  Wait for next request from client
       print "Waiting for message"
       work = consumer_receiver.recv_json()
       #socket.send(json.dumps("hello"))
       #continue
       print "Received request: ", work
       data = json.loads(work)
       host = data['host'] #TODO: rename this to host_ip
       #TODO: add support for host port (default 23)
       connector = data['connector']
       username = data['username']
       password = data['password']
       command = data['command']
       message_key = data['message_key']
       vtysh = data.get('vtysh', False)
       message_key = str(message_key)
       username = str(username)
       password = str(password)
       command = str(command)
       print "command is", command
       data = {k: str(v) for k, v in data.items()}
       try:
         hostname, result = do_connect(**data)
         success = True
       except Exception, e:
        print e
        hostname = ""
        success = False
        result = str(e)
        if "No route to host" in e:
          # simpler message
          result = "No route to host"
        if "pexpect.TIMEOUT" in str(e):
          #TODO: test for timeout exception directly
          result = "Pexpect timeout"
       finally:
        try:
          data = str(data)
          hostname = str(hostname)
          result = str(result)
          message = json.dumps({'command': work,
            "success": success,
            'hostname': hostname,
            'result': result})
        except Exception, e:
          print "cant dump", e
        else:
          consumer_sender.send("%s %s" % (message_key, message))
          print "Sent to zmq"

def main():
  num_worker_threads = 5
  try:
    num_worker_threads = int(sys.argv[1])
  except IndexError:
    pass
  #NOTE: need pts/x available for worst-case of all threads at once
  for i in range(num_worker_threads):
      t = Thread(target=worker)
      t.daemon = True
      t.start()


  # start the streamer device
  streamer_device(5559, 5560)
  forwarder_device(5561, 5562)

  while True:
      time.sleep(1)

if __name__ == "__main__":
  main()
