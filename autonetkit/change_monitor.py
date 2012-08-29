import networkx as nx
import os

def check_for_change(input_file, anm):
     timestamp_file = os.stat(input_file).st_mtime
     timestamp_graph = anm.overlay.input._graph.graph['timestamp']
     return timestamp_file != timestamp_graph


