import json
import networkx as nx
from networkx.readwrite import json_graph
import netaddr
import string
import autonetkit.anm

def stringify_netaddr(graph):
    import netaddr
# converts netaddr from iterables to strings so can use with json
    replace_as_string = set([netaddr.ip.IPAddress, netaddr.ip.IPNetwork])
#TODO: see if should handle dict specially, eg expand to __ ?

    for key, val in graph.graph.items():
        if type(val) in replace_as_string:
            graph.graph[key] = str(val)

    for node, data in graph.nodes(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph.node[node][key] = str(val)

    for src, dst, data in graph.edges(data=True):
        for key, val in data.items():
            if type(val) in replace_as_string:
                graph[src][dst][key] = str(val)

    return graph

class AnkEncoder(json.JSONEncoder):
    """Handles netaddr objects by converting to string form"""
    def default(self, obj):
        if isinstance(obj, netaddr.IPAddress):
            return str(obj)
        if isinstance(obj, netaddr.IPNetwork):
            return str(obj)
        if isinstance(obj, autonetkit.anm.overlay_node):
            return str(obj) #TODO: need to deserialize nodes back to anm?

        return json.JSONEncoder.default(self, obj)

def ank_json_dumps(graph, indent = 4):
    data =  json_graph.node_link_data(graph)
#TODO: use regex to convert IPAddress and IPNetwork back to respective form in decoder
    data = json.dumps(data, cls=AnkEncoder, indent = indent)
    return data

def ank_json_loads(data):
    data = json.loads(data)
    print data
    data = data['anm']['ip']
    print "data is", data
    def dict_to_object(d):
        inst = d
        for key, val in d.items():
            try:
                dot_count = string.count(val, ".")
                if dot_count:
# could be an IP or network address
                    if "/" in val:
                        try:
                            inst[key] = netaddr.IPNetwork(val)
                        except netaddr.core.AddrFormatError:
                            pass # unable to convert, leave as string
                    else:
                        try:
                            inst[key] = netaddr.IPAddress(val)
                        except netaddr.core.AddrFormatError:
                            pass # unable to convert, leave as string
            except AttributeError:
                pass # not a string

        return inst

    d = json.loads(data, object_hook=dict_to_object)
    print d
    return json_graph.node_link_graph(d)


def jsonify_anm(anm):
    """ Returns a dictionary of json-ified overlay graphs"""
    anm_json = {}
    graphics_graph = anm["graphics"]._graph.copy()
    for overlay_id in anm.overlays():
        overlay_graph = anm[overlay_id]._graph.copy()
        overlay_graph = stringify_netaddr(overlay_graph)
# JSON writer doesn't handle 'id' already present in nodes
                    #for n in graph:
                                #del graph.node[n]['id']

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

        x = (overlay_graph.node[n]['x'] for n in overlay_graph)
        y = (overlay_graph.node[n]['y'] for n in overlay_graph)
        x_min = min(x)
        y_min = min(y)
        for n in overlay_graph:
            overlay_graph.node[n]['x'] += - x_min
            overlay_graph.node[n]['y'] += - y_min


# strip out graph data
        overlay_graph.graph = {} #TODO: check why need to do this - should we just check for ip addresses eg in ip overlay? eg in a try/except loop?
        data = ank_json_dumps(overlay_graph)
        anm_json[overlay_id] = data
    return anm_json

def jsonify_nidb(nidb):
    print "NIDB"
    graph = nidb._graph
    for node in graph:
        graph.node[node]['x'] = graph.node[node]['graphics']['x']
        graph.node[node]['y'] = graph.node[node]['graphics']['y']
        graph.node[node]['device_type'] = graph.node[node]['graphics']['device_type']
        graph.node[node]['device_subtype'] = graph.node[node]['graphics']['device_subtype']
        try:
            print graph.node[node]['asn']
        except KeyError:
            print "no asn for", node

    x = (graph.node[n]['x'] for n in graph)
    y = (graph.node[n]['y'] for n in graph)
    x_min = min(x)
    y_min = min(y)
    for n in graph:
        graph.node[n]['x'] += - x_min
        graph.node[n]['y'] += - y_min

    data = ank_json_dumps(graph)
    print data
    return data

def dumps(anm, nidb = None):
    data = jsonify_anm(anm)
    if nidb:
        data['nidb'] = jsonify_nidb(nidb)
#TODO: need to update messaging format when have nidb also (as 'anm': won't be correct)
    json_data = json.dumps({'anm': data})
    return json_data
