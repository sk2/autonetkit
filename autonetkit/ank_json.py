import json
import logging
import string

import autonetkit.anm
import autonetkit.log as log
import autonetkit.nidb
import autonetkit.plugins
import autonetkit.plugins.ipv4
import netaddr
import networkx as nx
from networkx.readwrite import json_graph


class AnkEncoder(json.JSONEncoder):
    """Handles netaddr objects by converting to string form"""
    #TODO: look at using skipkeys = True to skip non-basic type keys (can we warn on this?)
    def default(self, obj):
        if isinstance(obj, set):
            return str(obj)
        if isinstance(obj, netaddr.IPAddress):
            return str(obj)
        if isinstance(obj, netaddr.IPNetwork):
            return str(obj)
        if isinstance(obj, autonetkit.nidb.nidb_node):
            #TODO: need to unserialize nidb nodes...
            return str(obj)
        if isinstance(obj, autonetkit.anm.OverlayNode):
            #TODO: add documentation about serializing anm nodes
            #TODO: remove now?
            log.warning("%s is anm overlay_node. Use attribute rather than object in compiler." % obj)
            return str(obj)
        if isinstance(obj, autonetkit.plugins.ipv4.TreeNode):
            #TODO: remove now?
            #TODO: add documentation about serializing anm nodes
            return str(obj)
        if isinstance(obj, autonetkit.anm.OverlayEdge):
            #TODO: add documentation about serializing anm nodes
            #TODO: remove now?
            log.warning("%s is anm overlay_edge. Use attribute rather than object in compiler." % obj)
            return str(obj)
        if isinstance(obj, autonetkit.nidb.config_stanza):
            retval = obj.to_json()
            return retval
        if isinstance(obj, autonetkit.nidb.overlay_interface):
            #TODO: check this is consistent with deserialization
            return str(obj)
        if isinstance(obj, nx.classes.Graph):
            #TODO: remove now?
            return json_graph.node_link_data(obj)

        if isinstance(obj, logging.LoggerAdapter):
            #TODO: filter this out in the to_json methods
            return ""

        return json.JSONEncoder.default(self, obj)

def ank_json_dumps(graph, indent = 4):
    data =  json_graph.node_link_data(graph)
#TODO: use regex to convert IPAddress and IPNetwork back to respective form in decoder
    data = json.dumps(data, cls=AnkEncoder, indent = indent, sort_keys = True)
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

def restore_anm_nidb_from_json(data):
    # This can be used to extract from the json used to send to webserver

    d = ank_json_custom_loads(data)
    anm = autonetkit.anm.AbstractNetworkModel()
    nidb = autonetkit.nidb.NIDB()

    for overlay_id, overlay_data in d.items():
        if overlay_id == "nidb":
            continue # don't restore nidb graph to anm
        anm._overlays[overlay_id] = json_graph.node_link_graph(overlay_data)

    nidb._graph = json_graph.node_link_graph(d['nidb'])
    rebind_interfaces(anm)

    return anm, nidb


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
            if isinstance(val, dict) and val.get("_config_stanza") == True:
                val = autonetkit.nidb.config_stanza(**val)
                inst[key] = val # update with (possibly) updated list

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

def rebind_interfaces(anm):
    for overlay_id in anm.overlays():
        overlay = anm[overlay_id]
        #for edge in overlay.edges():
            #unbound_interfaces = edge._interfaces
## map nodes -> node objects, values to integers (not strings)
            #interfaces = {overlay.node(key): val for key, val in unbound_interfaces.items()}
            #edge._interfaces = interfaces # store with remapped node
        for node in overlay.nodes():
            unbound_interfaces = node._interfaces
            if len(unbound_interfaces): # is list if none set
                interfaces = {int(key): val for key, val in unbound_interfaces.items()}
                node._interfaces = interfaces

#TODO: need to also rebind_interfaces for nidb

def rebind_nidb_interfaces(nidb):
    for node in nidb.nodes():
        unbound_interfaces = node._interfaces
        if len(unbound_interfaces): # is list if none set
            interfaces = {int(key): val for key, val in unbound_interfaces.items()}
            node._interfaces = interfaces


def ank_json_loads(data):
    d = ank_json_custom_loads(data)
    return json_graph.node_link_graph(d)

def jsonify_anm(anm):
    """ Returns a dictionary of json-ified overlay graphs"""
    anm_json = {}
    for overlay_id in anm.overlays():
        OverlayGraph = anm[overlay_id]._graph.copy()
        for n in OverlayGraph:
            try:
                del OverlayGraph.node[n]['id']
            except KeyError:
                pass
        anm_json[overlay_id] = ank_json_dumps(OverlayGraph)
    return json.dumps(anm_json)


def shortened_interface(name):
    """Condenses interface name. Not canonical - mainly for brevity"""
    name = name.replace("GigabitEthernet", "ge")
    name = name.replace("0/0/0/", "")
    return name

def jsonify_anm_with_graphics(anm, nidb = None):
    """ Returns a dictionary of json-ified overlay graphs, with graphics data appended to each overlay"""
    anm_json = {}
    test_anm_data = {}
    graphics_graph = anm["graphics"]._graph.copy()
    phy_graph = anm["phy"]._graph  # to access ASNs
    for overlay_id in anm.overlays():
        OverlayGraph = anm[overlay_id]._graph.copy()

    #TODO: don't regen x,y for each overlay - persist (possibly across all layers?)
    # for speed/clarity, get the graphics data to a dict and then set x,y if not set
    # then read from this

#TODO: only update, don't over write if already set
        for n in OverlayGraph:
            if n in graphics_graph:
                OverlayGraph.node[n].update( {
                'x': graphics_graph.node[n].get('x'),
                'y': graphics_graph.node[n].get('y'),
                'asn': graphics_graph.node[n]['asn'],
                'label': graphics_graph.node[n]['label'],
                'device_type': graphics_graph.node[n]['device_type'],
                'device_subtype': graphics_graph.node[n].get('device_subtype'),
                'pop': graphics_graph.node[n].get('pop'),
                })

                #TODO: if no label set, then use node if
            elif n in phy_graph:
                #TODO: if in phy but x/y not set, then fall through to setting random
                #TODO: tidy by moving x/y to higher up before each overlay
                # try to copy x/y from phy
                OverlayGraph.node[n].update( {
                        'x': phy_graph.node[n].get('x'),
                        'y': phy_graph.node[n].get('y'),
                        'asn': phy_graph.node[n]['asn'],
                        'label': phy_graph.node[n]['label'],
                        'device_type': phy_graph.node[n]['device_type'],
                        'device_subtype': phy_graph.node[n].get('device_subtype'),
                        'pop': phy_graph.node[n].get('pop'),
                })
            else:
                import random
                log.debug("Converting to graphics JSON format: node %s not in graphics overlay" % n)
                #TODO: see if can key off node hash - so doesn't move nodes around
                if OverlayGraph.node[n].get("x") is None:
                    OverlayGraph.node[n]['x'] = random.randint(0,800)
                if OverlayGraph.node[n].get("y") is None:
                    OverlayGraph.node[n]['y'] =random.randint(0,800)
                if OverlayGraph.node[n].get("label") is None:
                    OverlayGraph.node[n]['label'] = n # set to node ID
                if OverlayGraph.node[n].get("device_type") is None:
                    OverlayGraph.node[n]['device_type'] = None # set to node ID


            if n in phy_graph:
                # use ASN from physical graph
                OverlayGraph.node[n]['asn'] = phy_graph.node[n].get("asn")

            try:
                del OverlayGraph.node[n]['id']
            except KeyError:
                pass

            if nidb:
                nidb_graph = nidb._graph
                if n in nidb:
                    nidb_node_data = nidb_graph.node[n]
                    try:
                        #TODO: check why not all nodes have _interfaces initialised
                        overlay_interfaces = OverlayGraph.node[n]["_interfaces"]
                    except KeyError:
                        continue # skip copying interface data for this node

                    for interface_id in overlay_interfaces.keys():
                        try:
                            nidb_interface_id = nidb_node_data['_interfaces'][interface_id]['id']
                        except KeyError:
                            #TODO: check why arrive here - something not initialised?
                            continue
                        OverlayGraph.node[n]['_interfaces'][interface_id]['id'] = nidb_interface_id
                        id_brief = shortened_interface(nidb_interface_id)
                        OverlayGraph.node[n]['_interfaces'][interface_id]['id_brief'] = id_brief

#TODO: combine these, and round as necessary
        x = (OverlayGraph.node[n]['x'] for n in OverlayGraph)
        y = (OverlayGraph.node[n]['y'] for n in OverlayGraph)
        try:
            x_min = min(x)
        except ValueError:
            x_min = 0
        try:
            y_min = min(y)
        except ValueError:
            y_min = 0

        border_offset = 20 # so don't plot right at edge
        for n in OverlayGraph:
            #TODO: do this once per node, rather than each time
            OverlayGraph.node[n]['x'] += - x_min + border_offset
            OverlayGraph.node[n]['y'] += - y_min + border_offset
            #TODO: make scale to graph size: if size is <100 dont apply
            #OverlayGraph.node[n]['x'] = round(OverlayGraph.node[n]['x']/25) * 25
            #OverlayGraph.node[n]['y'] = round(OverlayGraph.node[n]['y']/25) * 25

            # and round to the nearest grid size
            # for now round to nearest 10

        anm_json[overlay_id] = ank_json_dumps(OverlayGraph)
        test_anm_data[overlay_id] = OverlayGraph


    if nidb:
        test_anm_data['nidb'] = prepare_nidb(nidb)

    result = json.dumps(test_anm_data, cls=AnkEncoder, indent = 4, sort_keys = True)
    return result

def prepare_nidb(nidb):
    graph = nidb._graph
    for node in graph:
        if graph.node[node].get("graphics"):
            graph.node[node]['x'] = graph.node[node]['graphics']['x']
            graph.node[node]['y'] = graph.node[node]['graphics']['y']
            graph.node[node]['device_type'] = graph.node[node]['graphics']['device_type']
            graph.node[node]['device_subtype'] = graph.node[node]['graphics']['device_subtype']

        for interface_index in graph.node[node]['_interfaces']:
            try:
                interface_id = graph.node[node]["_interfaces"][interface_index]['id']
            except KeyError: # interface doesn't exist, eg for a lan segment
                interface_id = ""
            id_brief = shortened_interface(interface_id)
            graph.node[node]["_interfaces"][interface_index]['id_brief'] = id_brief

    x = (graph.node[n]['x'] for n in graph)
    y = (graph.node[n]['y'] for n in graph)
    x_min = min(x)
    y_min = min(y)
    for n in graph:
        graph.node[n]['x'] += - x_min
        graph.node[n]['y'] += - y_min

    return graph

def jsonify_nidb(nidb):
    graph = prepare_nidb(nidb)
    data = ank_json_dumps(graph)
    return data

def dumps(anm, nidb = None, indent = 4):
    return jsonify_anm_with_graphics(anm, nidb)
