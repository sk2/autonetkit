import glob
import os
import nidb

#TODO: make this generalise to two graphs, rather than NIDB specifically

def nidb_diff(directory = None, length = 1):
    if not directory:
        directory = os.path.join("versions", "nidb")
    glob_dir = os.path.join(directory, "*.json.gz")
    pickle_files = glob.glob(glob_dir)
    pickle_files = sorted(pickle_files)
    pairs = [(a, b) for (a, b) in zip(pickle_files, pickle_files[1:])]
    pairs = pairs[-1*length:]
    diffs = []
    for file_a, file_b in pairs:
        nidb_a = nidb.NIDB()
        nidb_a.restore(file_a)
        graph_a = nidb_a._graph
        nidb_b = nidb.NIDB()
        nidb_b.restore(file_b)
        graph_b = nidb_b._graph
        diff = compare(graph_a, graph_b)
        # remove render folder which is timestamps
        diffs.append(diff)

    return diffs

def elem_diff(elem_a, elem_b):
    if type(elem_a) != type(elem_b):
        return "different types"

    if isinstance(elem_a, dict):
        retval = {}
        keys_a = set(elem_a.keys())
        keys_b = set(elem_b.keys())
        added_keys = keys_b - keys_a
        if len(added_keys):
            retval['a'] = list(added_keys)
        removed_keys = keys_a - keys_b
        if len(removed_keys):
            retval['r'] = list(removed_keys)
        common_keys = keys_a & keys_b
        for key in common_keys:
            res = elem_diff(elem_a[key], elem_b[key])
            if res:
                retval[key] = res

        if len(retval):
            return retval

    if isinstance(elem_a, list):
        len_a = len(elem_a)
        len_b = len(elem_b)
#TODO: handle if different lengths
        retval = []
        min_len = min(len_a, len_b)
        for index in range(min_len):
            res = elem_diff(elem_a[index], elem_b[index])
            if res:
                retval.append(res)

        if any(retval):
            return retval

    if elem_a != elem_b:
        return {1: elem_a, 2: elem_b }

def compare(graph_a, graph_b):
    diff = {}

    diff = {
            'graph': {},
            'nodes': {},
            'edges': {},
            }

    diff['graph'] = elem_diff(graph_a.graph, graph_b.graph)

    nodes_a = set(graph_a.nodes())
    nodes_b = set(graph_b.nodes())
    common_nodes = nodes_a & nodes_b
    added_nodes = nodes_b - nodes_a
    if added_nodes:
        diff['nodes']['a'] = list(added_nodes)
    removed_nodes = nodes_a - nodes_b
    if removed_nodes:
        diff['nodes']['r'] = list(removed_nodes)
    diff['nodes'] = {
            'm': {},
            }

    for node in common_nodes:
        dict_a = graph_a.node[node]
        dict_b = graph_b.node[node]
        node_diff = elem_diff(dict_a, dict_b)
        if node_diff:
            diff['nodes']['m'][node] = node_diff

    # remove empty if no changes
    if not len(diff['nodes']['m']):
        del diff['nodes']['m']

    #TODO: do this backwards, and append at end
    if not len(diff['nodes']):
        del diff['nodes']

    edges_a = set(graph_a.edges())
    edges_b = set(graph_b.edges())
    added_edges = edges_b - edges_a
    if added_edges:
        diff['edges']['a'] = list(added_edges)
    removed_edges = edges_a - edges_b
    if removed_edges:
        diff['edges']['r'] = list(removed_edges)

    diff['edges'] = {
            'm': {},
            }

    common_edges = edges_a & edges_b
    for (src, dst) in common_edges:
        dictA = graph_a[src][dst]
        dictB = graph_b[src][dst]
        edge_diff = elem_diff(dictA, dictB)
        if edge_diff:
            name = "%s_%s" % (src, dst)
            diff['edges']['m'][name] = edge_diff

    # remove empty if no changes
    if not len(diff['edges']['m']):
        del diff['edges']['m']

    #TODO: do this backwards, and append at end
    if not len(diff['edges']):
        del diff['edges']


    return diff

