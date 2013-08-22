import autonetkit
import os
import autonetkit.load.graphml as graphml
import shutil

automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

dirname, filename = os.path.split(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(dirname, os.pardir))

anm =  autonetkit.ANM()
input_file = os.path.join(parent_dir, "small_internet.graphml")
input_graph = graphml.load_graphml(input_file)

import autonetkit.build_network as build_network
anm = build_network.initialise(input_graph)
anm = build_network.apply_design_rules(anm)
anm['phy'].data.uuid = "my_uuid"



try:
	from websocket import create_connection
except ImportError:
	print "websocket-client package not installed"
else:
	autonetkit.update_http(anm)

	ws = create_connection("ws://localhost:8000/ws")
	ws.send("overlay_list")
	result =  ws.recv()
	expected = '{"overlay_list": ["bgp", "ebgp", "ebgp_v4", "ebgp_v6", "eigrp", graphics", "ibgp_v4", "ibgp_v6", "ibgp_vpn_v4", "input", "input_directed", "ip", "ipv4", "ipv6", "isis", "l3_conn", "ospf", "phy", "vrf"]}'
	assert(result == expected)

	overlay_id = "phy"
	ws.send("overlay_id=" + overlay_id)
	result =  ws.recv()
	with open(os.path.join(dirname, "expected_phy.json"), "r") as fh:
		expected = fh.read()

	assert(result == expected)
	ws.close()

	import autonetkit.console_script as console_script
	render_hostname = "localhost"

	nidb = console_script.create_nidb(anm)
	nidb._graph.graph['timestamp'] = "123456"

	import autonetkit.compilers.platform.netkit as pl_netkit
	nk_compiler = pl_netkit.NetkitCompiler(nidb, anm, render_hostname)
	nk_compiler.compile()
	autonetkit.update_http(anm, nidb)

	ws = create_connection("ws://localhost:8000/ws")
	ws.send("overlay_list")
	result =  ws.recv()
	expected = '{"overlay_list": ["bgp", "ebgp", "ebgp_v4", "ebgp_v6", "eigrp", graphics", "ibgp_v4", "ibgp_v6", "ibgp_vpn_v4", "input", "input_directed", "ip", "ipv4", "ipv6", "isis", "l3_conn", "nidb", "ospf", "phy", "vrf"]}'
	assert(result == expected)

	overlay_id = "nidb"
	ws.send("overlay_id=" + overlay_id)
	result =  ws.recv()
	with open(os.path.join(dirname, "expected_nidb.json"), "r") as fh:
		expected = fh.read()

	assert(result == expected)
	ws.close()

	#TODO: test highlight, and getting response back (needs callback, refer https://pypi.python.org/pypi/websocket-client/0.7.0)
