import networkx as nx
import glob
import os
import pprint
from collections import defaultdict

def diff_history(directory, length = 1):
    glob_dir = os.path.join(directory, "*.pickle.tar.gz")
    pickle_files = glob.glob(glob_dir)
    pickle_files = sorted(pickle_files)
    pairs = [(a, b) for (a, b) in zip(pickle_files, pickle_files[1:])]
    pairs = pairs[-1*length:]
    diffs = []
    for fileA, fileB in pairs:
        graphA = nx.read_gpickle(fileA)
        graphB = nx.read_gpickle(fileB)
        diff = compare(graphA, graphB)
        # remove render folder which is timestamps
        diffs.append(diff)

    return diffs

def element_diff(elemA, elemB):
    try: # split out if single element lists
        if len(elemA) == len(elemB) == 1:
            elemA = elemA[0]
            elemB = elemB[0]
    except TypeError:
        pass
    try:
        elemA.keys() # see if both are dicts
        elemB.keys()
        return dict_diff(elemA, elemB)
    except (TypeError, AttributeError):
        if isinstance(elemA, list) and  isinstance(elemB, list):
            if len(elemA) > 1 and len(elemB) > 1:
                return list_diff(elemA, elemB)
            else:
                pass # single element in each list, compare as elements
    if elemA == elemB:
        return #TODO: see why this performs different to elemA != elemB
    else:
        return { '1': elemA, '2': elemB, }

def list_diff(listA, listB):
    listA = sorted(listA)
    listB = sorted(listB)
    elements = zip(listA, listB)
#TODO: check if list different lengths
    list_changed = []
    for (elemA, elemB) in elements:
        try:
            elemA.keys() # see if both are dicts
            elemB.keys()
            elem_changed = dict_diff(elemA, elemB) # are dicts, compare as a dict
            if elem_changed:
                list_changed.append(elem_changed)
        except (TypeError, AttributeError):
            try:
                if len(elemA) > 1 and len(elemB) > 1:
                    elem_changed = list_diff(elemA, elemB)
                    if elem_changed:
                        list_changed.append(elem_changed)

            except AttributeError:
                return element_diff(elemA, elemB)

    if list_changed:
        if len(list_changed) == 1:
            return list_changed[0] # return as element
        return list_changed

def dict_diff(dictA, dictB):
    """Calls self recursively to see if any changes
    If no changes returns None, if changes, returns changes
    If no keys in self, returns None"""
    #TODO: if no keys then return items???
    #print "comparing", dictA, dictB
    diff = defaultdict(dict)
#TODO: start with elem diff
    try:
        keysA = set(dictA.keys())
        keysB = set(dictB.keys())
    except (TypeError, AttributeError):
# if list, compare list items
        element_modified = element_diff(dictA, dictB)
        if element_modified:
            return {'m': element_modified}
        return

#TODO: change commonKeys to common_keys

    commonKeys = keysA & keysB
    keys_modified = {}
    for key in commonKeys:
        subDictA = dictA[key]
        subDictB = dictB[key]
        changed = dict_diff(subDictA, subDictB)
        if changed:
            keys_modified[key] = changed

    keys_added = keysB - keysA
    if keys_added:
        diff['a'] = keys_added
    keys_removed = keysA - keysB
    if keys_removed:
        diff['r'] = keys_removed
    if keys_modified:
        diff['m'] = keys_modified

    if diff:
        return dict(diff)

def compare(graphA, graphB):
    diff = {}
    nodesA = set(graphA.nodes())
    nodesB = set(graphB.nodes())
    commonNodes = nodesA & nodesB
    diff = {
            'graph': {},
            'nodes': {},
            'edges': {},
            }
    diff['nodes'] = {
            'a': nodesB - nodesA,
            'r': nodesA - nodesB,
            'm': {},
            }

    for node in commonNodes:
        dictA = graphA.node[node]
        dictB = graphB.node[node]
        node_diff = dict_diff(dictA, dictB)
        if node_diff:
            diff['nodes']['m'][node] = node_diff

    edgesA = set(graphA.edges())
    edgesB = set(graphB.edges())
    diff['edges'] = {
            'a': edgesB - edgesA,
            'r': edgesA - edgesB,
            'm': {},
            }

    commonEdges = edgesA & edgesB
    for (src, dst) in commonEdges:
        dictA = graphA[src][dst]
        dictB = graphB[src][dst]
        edge_diff = dict_diff(dictA, dictB)
        if edge_diff:
            diff['edges']['m'][(src, dst)] = edge_diff


    return diff

