def get_results(server, commands, send_port = 5559, receive_port = 5562):
    import zmq
    import json
    import autonetkit.log as log
    import uuid # create key for unique zmq channel for replies
    message_key = uuid.uuid4()
    message_key = str(message_key)
    import autonetkit.ank_json as ank_json

    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUSH)
    zmq_socket.connect("tcp://%s:%s" % (server, send_port))

    context = zmq.Context()
    results_receiver = context.socket(zmq.SUB)
    results_receiver.connect("tcp://%s:%s" % (server, receive_port))
    results_receiver.setsockopt(zmq.SUBSCRIBE, message_key)
    #NOTE: need to connect *before* send commands in order to capture replies

    for command in commands:
        command["message_key"] = message_key

        work_message = json.dumps(command, cls=ank_json.AnkEncoder, indent=4)
        #print "sending", work_message
        log.debug("Sending %s to %s" % (command['command'], command['host']))
        zmq_socket.send_json(work_message)

    log.info("Collecting results")

    json_results = []
    log.debug("Expecting %s replies" % len(commands))
    for index in range(len(commands)):
        reply = results_receiver.recv()
        # extract the uuid key from start (36 chars long)
        data = reply[len(message_key):]
        result = json.loads(data)
        hostname = result["hostname"].replace(".", "_")
        json_results.append(result)
        command = json.loads(result["command"])
        host = command["host"]
        log.debug("%s/%s: Reply from %s (%s)" % (index,
            len(commands), hostname, host))
        yield result
    else:
        # cleanup
        results_receiver.close()