import autonetkit.console_script as console_script
import subprocess
import os
import sys
#from cStringIO import StringIO
import shutil
import autonetkit.log as log
import autonetkit

if False:
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