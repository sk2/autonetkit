import json
import networkx as nx
from networkx.readwrite import json_graph
import netaddr
import string
import autonetkit.anm
import autonetkit.log as log

class AnkEncoder(json.JSONEncoder):
    """Handles netaddr objects by converting to string form"""
    def default(self, obj):
        if isinstance(obj, set):
            return str(obj)
        if isinstance(obj, netaddr.IPAddress):
            return str(obj)
        if isinstance(obj, netaddr.IPNetwork):
            return str(obj)
        if isinstance(obj, autonetkit.anm.overlay_node):
            #TODO: add documentation about serializing anm nodes
            log.warning("%s is anm overlay_node. Use attribute rather than object in compiler." % obj)
            return str(obj)
        if isinstance(obj, autonetkit.plugins.ip.TreeNode):
            #TODO: add documentation about serializing anm nodes
            return str(obj)
        if isinstance(obj, autonetkit.anm.overlay_edge):
            #TODO: add documentation about serializing anm nodes
            log.warning("%s is anm overlay_edge. Use attribute rather than object in compiler." % obj)
            return str(obj)

        return json.JSONEncoder.default(self, obj)

def ank_json_dumps(graph, indent = 4):
    data =  json_graph.node_link_data(graph)
#TODO: use regex to convert IPAddress and IPNetwork back to respective form in decoder
    data = json.dumps(data, cls=AnkEncoder, indent = indent)
    return data


def string_to_netaddr(val):
    retval = None
    dot_count = string.count(val, ".")
    if dot_count:
# could be an IP or network address
        if "/" in val:
            try:
                retval = netaddr.IPNetwork(val)
            except netaddr.core.AddrFormatError:
                return # unable to convert, leave as string
        else:
            try:
                retval = netaddr.IPAddress(val)
            except netaddr.core.AddrFormatError:
                return # unable to convert, leave as string

    return retval

def ank_json_custom_loads(data):
    #data = json.loads(data) # this is needed if dicts contain anm overlays, nidb, etc
    def dict_to_object(d):
        inst = d
        for key, val in d.items():
            try:
                newval = string_to_netaddr(val)
                if newval:
                    inst[key] = newval
            except AttributeError:
                pass # not a string
# handle lists of IP addresses
            
            if isinstance(val, list):
                if any(isinstance(elem, basestring) for elem in val):
                    # list contains a string
                    for index, elem in enumerate(val):
                        try:
                            new_elem = string_to_netaddr(elem)
                            if new_elem:
                                val[index] = new_elem # in-place replacement
                        except AttributeError:
                            pass # not a string

                inst[key] = val # update with (possibly) updated list

        return inst

    d = json.loads(data, object_hook=dict_to_object)
    return d


def ank_json_loads(data):
    d = ank_json_custom_loads(data)
    return json_graph.node_link_graph(d)

def jsonify_anm(anm):
    """ Returns a dictionary of json-ified overlay graphs"""
    anm_json = {}
    for overlay_id in anm.overlays():
        overlay_graph = anm[overlay_id]._graph.copy()
        for n in overlay_graph:
            try:
                del overlay_graph.node[n]['id']
            except KeyError:
                pass
        anm_json[overlay_id] = ank_json_dumps(overlay_graph)
    return json.dumps(anm_json)


def jsonify_anm_with_graphics(anm):
    """ Returns a dictionary of json-ified overlay graphs, with graphics data appended to each overlay"""
    anm_json = {}
    graphics_graph = anm["graphics"]._graph.copy()
    for overlay_id in anm.overlays():
        overlay_graph = anm[overlay_id]._graph.copy()


#TODO: only update, don't over write if already set
        for n in overlay_graph:
            overlay_graph.node[n].update( {
                'x': graphics_graph.node[n]['x'],
                'y': graphics_graph.node[n]['y'],
                'asn': graphics_graph.node[n]['asn'],
                'device_type': graphics_graph.node[n]['device_type'],
                'device_subtype': graphics_graph.node[n].get('device_subtype'),
                'pop': graphics_graph.node[n].get('pop'),
                })

            try:
                del overlay_graph.node[n]['id']
            except KeyError:
                pass

#TODO: combine these, and round as necessary
        x = (overlay_graph.node[n]['x'] for n in overlay_graph)
        y = (overlay_graph.node[n]['y'] for n in overlay_graph)
        try:
            x_min = min(x)
        except ValueError:
            x_min = 0
        try:
            y_min = min(y)
        except ValueError:
            y_min = 0
        for n in overlay_graph:
            overlay_graph.node[n]['x'] += - x_min
            overlay_graph.node[n]['y'] += - y_min

        anm_json[overlay_id] = ank_json_dumps(overlay_graph)
    return anm_json

def jsonify_nidb(nidb):
    graph = nidb._graph
    for node in graph:
        graph.node[node]['x'] = graph.node[node]['graphics']['x']
        graph.node[node]['y'] = graph.node[node]['graphics']['y']
        graph.node[node]['device_type'] = graph.node[node]['graphics']['device_type']
        graph.node[node]['device_subtype'] = graph.node[node]['graphics']['device_subtype']

    x = (graph.node[n]['x'] for n in graph)
    y = (graph.node[n]['y'] for n in graph)
    x_min = min(x)
    y_min = min(y)
    for n in graph:
        graph.node[n]['x'] += - x_min
        graph.node[n]['y'] += - y_min

    data = ank_json_dumps(graph)
    return data

def dumps(anm, nidb = None):
    data = jsonify_anm_with_graphics(anm)
    if nidb:
        data['nidb'] = jsonify_nidb(nidb)
#TODO: need to update messaging format when have nidb also (as 'anm': won't be correct)
    json_data = json.dumps({'anm': data})
    return json_data
