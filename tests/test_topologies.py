import autonetkit.console_script as console_script
import subprocess
import os
import sys
#from cStringIO import StringIO
import shutil
import autonetkit.log as log

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
]


automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

for topology in topologies:
    print "Testing topology", topology
    compare_output_expected(topology, automated = automated)
