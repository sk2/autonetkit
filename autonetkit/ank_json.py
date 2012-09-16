import json
import networkx as nx
from networkx.readwrite import json_graph

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
        data = json_graph.dumps(overlay_graph, indent=4)
        anm_json[overlay_id] = data
    return anm_json

def jsonify_nidb(nidb):
    return
    print "nidb", nidb
    overlay_graph = nidb._graph.copy()
    print overlay_graph.nodes()
#TODO: need to go deeper than one level for nidb
    #overlay_graph = stringify_netaddr(overlay_graph)
    overlay_graph.graph = {} 
    
    data = json_graph.dumps(overlay_graph, indent=4)
    return data
    return
    """processing to make web friendly.
    Handling netaddr which won't JSON serialize, and appending graphics data to overlay"""
    overlay_graph = anm[overlay_id]._graph.copy()
    graphics_graph = anm["graphics"]._graph.copy()
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

                # remove leading space
    x = (overlay_graph.node[n]['x'] for n in overlay_graph)
    y = (overlay_graph.node[n]['y'] for n in overlay_graph)
    x_min = min(x)
    y_min = min(y)
    for n in overlay_graph:
        overlay_graph.node[n]['x'] += - x_min
        overlay_graph.node[n]['y'] += - y_min


# strip out graph data
    overlay_graph.graph = {}
    data = json_graph.dumps(overlay_graph, indent=4)

def dumps(anm, nidb = None):
    data = jsonify_anm(anm)
    if nidb:
        data['nidb'] = jsonify_nidb(nidb)
    json_data = json.dumps(data)
    return json_data
