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
        if isinstance(obj, autonetkit.nidb.DmNode):
            #TODO: need to unserialize nidb nodes...
            return str(obj)
        if isinstance(obj, autonetkit.anm.NmEdge):
            log.warning("%s is anm overlay_edge. Use attribute rather than object in compiler." % obj)
            return str(obj)
        if isinstance(obj, autonetkit.nidb.ConfigStanza):
            retval = obj.to_json()
            return retval
        if isinstance(obj, autonetkit.nidb.DmInterface):
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
    nidb = autonetkit.nidb.DeviceModel()

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
            if isinstance(val, dict) and val.get("_ConfigStanza") == True:
                val = autonetkit.nidb.ConfigStanza(**val)
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
            #unbound_ports = edge._ports
## map nodes -> node objects, values to integers (not strings)
            #interfaces = {overlay.node(key): val for key, val in unbound_ports.items()}
            #edge._ports = interfaces # store with remapped node
        for node in overlay.nodes():
            unbound_ports = node.raw_interfaces
            if len(unbound_ports): # is list if none set
                interfaces = {int(key): val for key, val in unbound_ports.items()}
                node.raw_interfaces = interfaces

#TODO: need to also rebind_interfaces for nidb

def rebind_nidb_interfaces(nidb):
    for node in nidb.nodes():
        unbound_ports = node.raw_interfaces
        if len(unbound_ports): # is list if none set
            interfaces = {int(key): val for key, val in unbound_ports.items()}
            node.raw_interfaces = interfaces


def ank_json_loads(data):
    d = ank_json_custom_loads(data)
    return json_graph.node_link_graph(d)

def jsonify_anm(anm):
    """ Returns a dictionary of json-ified overlay graphs"""
    anm_json = {}
    for overlay_id in anm.overlays():
        NmGraph = anm[overlay_id]._graph.copy()
        for n in NmGraph:
            try:
                del NmGraph.node[n]['id']
            except KeyError:
                pass
        anm_json[overlay_id] = ank_json_dumps(NmGraph)
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

    import random
    from collections import defaultdict
    attribute_cache = defaultdict(dict)
    # the attributes to copy
    # TODO: check behaviour for None if explicitly set
    #TODO: need to check if attribute is set in overlay..... using API
    copy_attrs =  ["x", "y", "asn", "label", "device_type", "device_subtype"]
    for node, in_data in phy_graph.nodes(data=True):
      out_data = {key: in_data.get(key) for key in copy_attrs
      if key in in_data}
      attribute_cache[node].update(out_data)

    # Update for graphics (over-rides phy)
    for node, in_data in graphics_graph.nodes(data=True):
      out_data = {key: in_data.get(key) for key in copy_attrs
      if key in in_data}
      attribute_cache[node].update(out_data)

    for overlay_id in anm.overlays():
        print overlay_id

        from networkx.readwrite import json_graph
        import json
        data =  json_graph.node_link_data(anm[overlay_id]._graph)
        with open("%s.json" % overlay_id, "w") as fh:
            result = json.dumps(data, cls=AnkEncoder, indent = 4, sort_keys = True)
            fh.write(result)

        nm_graph = anm[overlay_id]._graph.copy()

        for node in nm_graph:
            node_data = dict(attribute_cache.get(node, {}))
            # update with node data from this overlay
            #TODO: check is not None won't clobber specifically set in overlay...
            graph_node_data = nm_graph.node[node]
            overlay_node_data = {key: graph_node_data.get(key)
                for key in copy_attrs if key in graph_node_data}
            node_data.update(overlay_node_data)

            # check for any non-set properties
            if node_data.get("x") is None:
                new_x = random.randint(0,800)
                node_data['x'] = new_x
                # store for other graphs to use
                log.debug("Allocated random x %s to node %s in overlay %s" %
                    (new_x, node, overlay_id))
                attribute_cache[node]['x'] = new_x
            if node_data.get("y") is None:
                new_y = random.randint(0,800)
                node_data['y'] =new_y
                # store for other graphs to use
                attribute_cache[node]['y'] =new_y
                log.debug("Allocated random y %s to node %s in overlay %s" %
                    (new_y, node, overlay_id))

            if node_data.get("label") is None:
                node_data['label'] = str(node) # don't need to cache

            # store on graph
            nm_graph.node[node] = node_data

            try:
                del nm_graph.node[node]['id']
            except KeyError:
                pass

            if nidb:
                nidb_graph = nidb.raw_graph()
                if node in nidb:
                    DmNode_data = nidb_graph.node[node]
                    try:
                        #TODO: check why not all nodes have _ports initialised
                        overlay_interfaces = nm_graph.node[node]["_ports"]
                    except KeyError:
                        continue # skip copying interface data for this node

                    for interface_id in overlay_interfaces.keys():
                        #TODO: use raw_interfaces here
                        try:
                            nidb_interface_id = DmNode_data['_ports'][interface_id]['id']
                        except KeyError:
                            #TODO: check why arrive here - something not initialised?
                            continue
                        nm_graph.node[node]['_ports'][interface_id]['id'] = nidb_interface_id
                        id_brief = shortened_interface(nidb_interface_id)
                        nm_graph.node[node]['_ports'][interface_id]['id_brief'] = id_brief

        anm_json[overlay_id] = ank_json_dumps(nm_graph)
        test_anm_data[overlay_id] = nm_graph


    if nidb:
        test_anm_data['nidb'] = prepare_nidb(nidb)

    result = json.dumps(test_anm_data, cls=AnkEncoder, indent = 4, sort_keys = True)
    return result

def prepare_nidb(nidb):
    graph = nidb.raw_graph()
    for node in graph:
        if graph.node[node].get("graphics"):
            graph.node[node]['x'] = graph.node[node]['graphics']['x']
            graph.node[node]['y'] = graph.node[node]['graphics']['y']
            graph.node[node]['device_type'] = graph.node[node]['graphics']['device_type']
            graph.node[node]['device_subtype'] = graph.node[node]['graphics']['device_subtype']

        for interface_index in graph.node[node]['_ports']:
            try:
                interface_id = graph.node[node]["_ports"][interface_index]['id']
            except KeyError: # interface doesn't exist, eg for a lan segment
                interface_id = ""
            id_brief = shortened_interface(interface_id)
            graph.node[node]["_ports"][interface_index]['id_brief'] = id_brief

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
