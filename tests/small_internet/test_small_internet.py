import autonetkit
import autonetkit.load.graphml as graphml
import os
import gzip
import json
import unittest
import subprocess
import shutil

def gzip_to_json(filename):
    with gzip.open(filename, "r") as json_fh:
        return json.load(json_fh)

def json_to_gzip(data, filename):
    with gzip.open(filename, "wb") as json_fh:
        return json.dump(data, json_fh)

automated = True # whether to open ksdiff, log to file...
if __name__ == "__main__":
    automated = False

dirname, filename = os.path.split(os.path.abspath(__file__))

anm =  autonetkit.ANM()
input_file = os.path.join(dirname, "small_internet.graphml")
input_graph = graphml.load_graphml(input_file)

import autonetkit.build_network as build_network
anm = build_network.initialise(input_graph)
anm = build_network.apply_design_rules(anm)

import autonetkit.console_script as console_script
render_hostname = "localhost"

nidb = console_script.create_nidb(anm)
nidb_a = nidb # store for diffing
nk_compiler = autonetkit.compiler.NetkitCompiler(nidb, anm, render_hostname)
nk_compiler.compile()

import autonetkit.render
autonetkit.render.render(nidb)

import os
dst_folder = nidb.topology['localhost'].render_dst_folder

# test folder structure
dir_structure = {}
for path, dirs, files in os.walk(dst_folder):
    dir_structure[path] = list(files)

# record folder structure
structure_filename = os.path.join(dirname, "dir_structure_expected.tar.gz")
json_to_gzip(dir_structure, structure_filename)
dir_structure_expected = gzip_to_json(structure_filename)
assert dir_structure == dir_structure_expected

routernames = ["as1r1", "as20r3"]
config_files = ["bgpd.conf", "ospfd.conf", "zebra.conf"]

for routername in routernames:
    router = nidb.node(routername)
    zebra_dir = os.path.join(router.render.base_dst_folder, "etc", "zebra")

    for conf_file in config_files:
        expected_filename = os.path.join(dirname, "%s_%s" % (routername, conf_file))
        with open(expected_filename, "r") as fh:
            expected_result = fh.read()

        actual_filename = os.path.join(zebra_dir, conf_file)
        with open(actual_filename, "r") as fh:
            actual_result = fh.read()

        if expected_result != actual_result:
            if automated:
                #TODO: use difflib
                print "Expected"
                print expected_result
                print "Actual"
                print actual_result
                raise AssertionError("Invalid result")
            else:
                cmd = ["ksdiff", expected_filename, actual_filename]
                child = subprocess.Popen(cmd)
                answer = raw_input("Merge (answer yes to merge): ")
                if answer == "yes":
                    print "Replacing expected with output"
                    shutil.move(actual_filename, expected_filename)
