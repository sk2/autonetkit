import networkx as nx
import os
import autonetkit.log as log

def check_for_change(input_file, anm):
    timestamp_file = os.stat(input_file).st_mtime
    timestamp_graph = anm.timestamp
    print timestamp_graph, timestamp_file
    return timestamp_file != timestamp_graph
