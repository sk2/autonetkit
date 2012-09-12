import networkx as nx
import os

def check_for_change(input_file, anm):
    print "input_file", input_file, "anm", anm
    timestamp_file = os.stat(input_file).st_mtime
    print anm['input']._graph.graph
    timestamp_graph = anm.timestamp
    return timestamp_file != timestamp_graph
