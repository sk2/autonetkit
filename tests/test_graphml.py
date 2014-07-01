import autonetkit.console_script as console_script
import subprocess
import os
import sys
#from cStringIO import StringIO
import shutil
import autonetkit.log as log
import autonetkit
import autonetkit.load.graphml as graphml


# stdio redirect from stackoverflow.com/q/2654834

#TODO: add feature that reports if only IP addresses have changed: match the diff to an IP regex

def compare_output_expected(topology_name, automated = True):
    log.info("Testing %s" % topology_name)
    input_filename = "%s.graphml" % topology_name

    dirname, filename = os.path.split(os.path.abspath(__file__))
    input_file = os.path.join(dirname, input_filename)

    arg_string = "-f %s --quiet --render" % input_file
    args = console_script.parse_options(arg_string)

    console_script.main(args)

    #TODO: check the output files

topologies = [
"small_internet",
"Aarnet",
"multigraph",
]


automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

for topology in topologies:
    print "Testing topology", topology
    compare_output_expected(topology, automated = automated)


# special case testing
def build_anm(topology_name):
    print "Building anm for %s" % topology_name
    dirname, filename = os.path.split(os.path.abspath(__file__))
    input_filename = os.path.join(dirname, "%s.graphml" % topology_name)

    anm =  autonetkit.NetworkModel()
    input_graph = graphml.load_graphml(input_filename)

    import autonetkit.build_network as build_network
    anm = build_network.initialise(input_graph)
    anm = build_network.apply_design_rules(anm)
    return anm

def test():
    anm = build_anm("blank_labels")
    actual_labels = sorted(anm['phy'].nodes())
    expected_labels = ["none___0", "none___1", "none___2"]
    assert(actual_labels == expected_labels)

    anm = build_anm("duplicate_labels")
    actual_labels = sorted(anm['phy'].nodes())
    expected_labels = ["none___0", "none___1", "none___2"]
    #TODO: need to log this as a bug
    #assert(actual_labels == expected_labels)

    anm = build_anm("asn_zero")
    actual_asns = [n.asn for n in anm['phy']]
    expected_asns = [1, 1, 1]
    assert(actual_asns == expected_asns)