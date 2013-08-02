"""Zmq based measurement server"""

import zmq
import json
import socket as python_socket
import telnetlib
from threading import Thread
import time
import sys

def do_connect(host, username, password, command, vtysh = False):
    #Note: user prompt and priv prompt have same password
    print host, username, password, command, vtysh

    print "Connecting to %s" % (host)
    try:
        tn = telnetlib.Telnet(host, timeout = 10)
    except Exception, e:
        print "Unable to connect to %s: %s" % (host, e)

    tn.set_debuglevel(0)
    print "Connected to %s" % host

    welcome_banner = tn.read_until("login:", timeout = 10)
    last_line = welcome_banner.splitlines()[-1]
    hostname = last_line.replace("login:", "").strip()

    linux_prompt = hostname + ":~#"

    print "Hostname is %s" % hostname

    #TODO: check why need the below for ascii/unicode/pzmq?
    username = str(username)
    password = str(password)
    command = str(command)
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
    return result

port = "5560" # TODO: make this side IPC

def worker(socket):
     while True:
           #  Wait for next request from client
           print "Waiting for message"
           message = socket.recv()
           #socket.send(json.dumps("hello"))
           #continue
           print type(message)
           print "Received request: ", message
           data = json.loads(message)
           print data
           host = data['host']
           username = data['username']
           password = data['password']
           command = data['command']
           vtysh = data.get('vtysh', False)
           print "command is", command
           try:
               result = do_connect(host, username, password, command, vtysh)
           except python_socket.timeout:
              pass
           else:
               message = json.dumps(result)
               socket.send(message)



def main():
  num_worker_threads = 10
  try:
    num_worker_threads = int(sys.argv[1])
  except IndexError:
    pass
  #NOTE: need pts/x available for worst-case of all threads at once
  for i in range(num_worker_threads):
      context = zmq.Context()
      socket = context.socket(zmq.REP)
      socket.connect("tcp://localhost:%s" % port)
      kwargs = {'socket': socket}
      t = Thread(target=worker, kwargs=kwargs)
      t.daemon = True
      t.start()

  while True:
      time.sleep(1)

if __name__ == "__main__":
  main()
