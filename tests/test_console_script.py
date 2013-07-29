import autonetkit.console_script as console_script
import subprocess
import os
import sys
#from cStringIO import StringIO
import shutil
import autonetkit.log as log
import autonetkit

# stdio redirect from stackoverflow.com/q/2654834

#TODO: add feature that reports if only IP addresses have changed: match the diff to an IP regex

automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

dirname, filename = os.path.split(os.path.abspath(__file__))

anm =  autonetkit.ANM()
input_file = os.path.join(dirname, "small_internet.graphml")
print input_file

arg_string = "-f %s --diff --render" % input_file
args = console_script.parse_options(arg_string)

console_script.main(args)