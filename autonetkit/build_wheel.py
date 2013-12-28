import os
from os.path import expanduser
import subprocess
import time
import shutil

cmd = ["python", "setup.py", "-V"]
child = subprocess.Popen(cmd, stdout=subprocess.PIPE)
version =  child.stdout.read().strip()

# Write the autonetkit version to a txt file to include in the autonetkit_cisco version
# (this is simpler than subclassing the setuptools module)

cmd = ["python", "setup.py", "clean", "bdist_wheel"]
"""
 Set WHEEL_TOOL env var as per
 https://wheel.readthedocs.org/en/latest/
 python setup.py bdist_wheel will automatically
 sign wheel files if the environment variable WHEEL_TOOL
 is set to the path of the wheel command line tool:
 """
# eg  $ export WHEEL_TOOL=/usr/local/bin/wheel
#TODO: look if other method to acheive this

new_env = os.environ.copy() # base on previous env, add new below:
new_env['WHEEL_TOOL'] = '/usr/local/bin/wheel'
child = subprocess.Popen(cmd, env = new_env, stdout=subprocess.PIPE)
for line in child.communicate():
    #print line
    pass

tar_file = "%s-%s-py27-none-any.whl" % ("autonetkit", version)
print tar_file
