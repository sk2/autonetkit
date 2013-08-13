import autonetkit.log as log
from autonetkit.collection.utils import get_results
import pkg_resources
import autonetkit.collection.process as ank_process
import autonetkit.ank_messaging as ank_messaging
import autonetkit
import json
import random
import autonetkit.console_script as console_script
import autonetkit.compilers.platform.netkit as pl_netkit
import os
import autonetkit.load.graphml as graphml
parse_template = pkg_resources.resource_filename("autonetkit", "textfsm/quagga/sh_ip_route")

emulation_server = "115.146.93.18"

anm = autonetkit.ANM()
anm.restore_latest()

nidb = autonetkit.NIDB()
nidb.restore_latest()
print list(nidb.nodes())

input_file = os.path.join("../../example/singleas.graphml")
input_graph = graphml.load_graphml(input_file)

import autonetkit.build_network as build_network
anm = build_network.initialise(input_graph)
anm = build_network.apply_design_rules(anm)

render_hostname = "localhost"

g_ospf = anm['ospf']
e1_8 = anm['ospf'].edge('5', '44')
print "before:", e1_8.cost
e1_8.cost = 1001
e1_8.apply_to_interfaces("cost")
print "after:", e1_8.cost

autonetkit.update_http(anm)

#nidb_a = nidb # copy original

nidb_b = console_script.create_nidb(anm)
render_hostname = "localhost"

platform_compiler = pl_netkit.NetkitCompiler(nidb_b, anm, render_hostname)
platform_compiler.compile()

autonetkit.update_http(anm, nidb_b)


import autonetkit.diff
diffs = autonetkit.diff.compare_nidb(nidb, nidb_b)
import pprint
pprint.pprint(diffs)


import autonetkit.push_changes
autonetkit.push_changes.apply_difference(nidb, diffs, emulation_server)

