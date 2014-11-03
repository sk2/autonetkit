import autonetkit.console_script as console_script
import os
import autonetkit
import autonetkit.load.graphml as graphml
import autonetkit.diff

automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

dirname, filename = os.path.split(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(dirname, os.pardir))

input_file = os.path.join(parent_dir, "small_internet.graphml")
input_graph = graphml.load_graphml(input_file)

import autonetkit.build_network as build_network
anm = build_network.initialise(input_graph)
anm = build_network.apply_design_rules(anm)

import autonetkit.console_script as console_script
render_hostname = "localhost"

g_phy = anm["input"]
g_test_a = anm.add_overlay("test_a")
g_test_b = anm.add_overlay("test_b")
g_test_a.add_nodes_from(g_phy)
g_test_b.add_nodes_from(g_phy)

g_test_a.add_edges_from(g_phy.edges())
g_test_b.add_edges_from(g_phy.edges())

g_test_b.remove_node("as300r1")

graph_a = g_test_a._graph
graph_b = g_test_b._graph

result = autonetkit.diff.compare(graph_a, graph_b)
result = str(result)

expected = "{'graph': None, 'nodes': {'r': ['as300r1']}, 'edges': {'r': [('as300r1', 'as300r3')]}}"

assert(result == expected)

#nidb_a = console_script.create_nidb(anm_a)
#import autonetkit.compilers.platform.netkit as pl_netkit
#nk_compiler = pl_netkit.NetkitCompiler(nidb_a, anm_a, render_hostname)
#nk_compiler.compile()
#
#anm_b = build_network.apply_design_rules(anm)
#nidb_b = console_script.create_nidb(anm_b)
#import autonetkit.compilers.platform.netkit as pl_netkit
#nk_compiler = pl_netkit.NetkitCompiler(nidb_b, anm_b, render_hostname)
#nk_compiler.compile()
#
#result = autonetkit.diff.compare_nidb(nidb_a, nidb_b)
#with open(os.path.join(dirname, "expected_diff.json"), "r") as fh:
#	expected = fh.read()
#
#with open(os.path.join(dirname, "result.json"), "w") as fh:
#	fh.write(str(result))
#
##print expected

#TODO: check match - once stable generation
#assert(expected == result)

if False:
	#Test NIDB level archived diffing
	# stdio redirect from stackoverflow.com/q/2654834

	#TODO: add feature that reports if only IP addresses have changed: match the diff to an IP regex

	automated = True # whether to open ksdiff, log to file...
	if __name__ == "__main__":
	    automated = False

	dirname, filename = os.path.split(os.path.abspath(__file__))
	parent_dir = os.path.abspath(os.path.join(dirname, os.pardir))

	anm =  autonetkit.ANM()
	input_file = os.path.join(parent_dir, "small_internet.graphml")
	arg_string = "-f %s --archive" % input_file
	args = console_script.parse_options(arg_string)
	console_script.main(args)


	dirname, filename = os.path.split(os.path.abspath(__file__))
	anm =  autonetkit.ANM()
	input_file = os.path.join(dirname, "small_internet_modified.graphml")
	arg_string = "-f %s --archive --diff" % input_file
	args = console_script.parse_options(arg_string)
	console_script.main(args)

	#TODO: need to compare diff versions.... and ignore timestamps... and find

	#shutil.rmtree("versions")