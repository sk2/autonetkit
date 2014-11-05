import autonetkit
from autonetkit import example
from collections import defaultdict
from networkx.readwrite import json_graph
settings = autonetkit.config.settings


def nx_to_simple(graph):
    j_data = json_graph.node_link_data(graph)

    # map ports to their named list
    port_index_mapping = defaultdict(dict)
    for node in j_data['nodes']:
        node_id = node['id']
        _ports = node['_ports']
        ports = []
        for index, port in _ports.items():
            try:
                port_id = port["id"]
            except KeyError:
                # no port id specified
                if index == 0:
                    port_id = "Loopback0"
                else:
                    port_id = "_port%s" % index

            port_data = dict(port)
            port_data['id'] = port_id
            ports.append(port_data)
            # record the mapping of index to port_id
            port_index_mapping[node_id][index] = port_id

        node['ports'] = sorted(ports, key=lambda x: x['id'])
        del node['_ports']

    nodes = j_data['nodes']
    mapped_links = []
    for link in j_data['links']:
        src_node = nodes[link['source']]['id']
        dst_node = nodes[link['target']]['id']
        src_int_index = link['_ports'][src_node]
        dst_int_index = link['_ports'][dst_node]
        src_int = port_index_mapping[src_node][src_int_index]
        dst_int = port_index_mapping[dst_node][dst_int_index]
        # link['ports'] = {'src': src_node, 'src_port': src_int,
        #                     'dst': dst_node, 'dst_port': dst_int}
        link['src'] = src_node
        link['src_port'] = src_int
        link['dst'] = dst_node
        link['dst_port'] = dst_int
        del link['_ports']
        try:
            del link['raw_interfaces']
        except KeyError:
            pass
        del link['source']
        del link['target']

    j_data['nodes'] = sorted(j_data['nodes'], key=lambda x: x['id'])
    j_data['links'] = sorted(
        j_data['links'], key=lambda x: (x['src'], x['dst']))

    return j_data


def simple_to_nx(j_data):
    port_to_index_mapping = defaultdict(dict)
    for node in j_data['nodes']:
        node_id = node['id']
        # first check for loopback zero
        ports = node['ports']
        _ports = {}  # output format
        try:
            lo_zero = [p for p in ports if p['id'] == "Loopback0"].pop()
        except IndexError:
            # can't pop -> no loopback zero, append
            lo_zero = {'category': 'loopback',
                       'description': "Loopback Zero"}
        else:
            ports.remove(lo_zero)
        finally:
            _ports[0] = lo_zero

        for index, port in enumerate(ports, start=1):
            _ports[index] = port
            port_to_index_mapping[node_id][port['id']] = index

        del node['ports']
        node['_ports'] = _ports

    nodes_by_id = {n['id']: i for i, n
                   in enumerate(j_data['nodes'])}

    unmapped_links = []

    mapped_links = j_data['links']

    for link in mapped_links:
        src = link['src']
        dst = link['dst']
        src_pos = nodes_by_id[src]
        dst_pos = nodes_by_id[dst]
        src_port_id = port_to_index_mapping[src][link['src_port']]
        dst_port_id = port_to_index_mapping[dst][link['dst_port']]

        interfaces = {src: src_port_id,
                      dst: dst_port_id}

        unmapped_links.append({'source': src_pos,
                               'target': dst_pos,
                               '_ports': interfaces
                               })

    j_data['links'] = unmapped_links
    return json_graph.node_link_graph(j_data)


def load_json(input_data, defaults = True):
    import json
    data = json.loads(input_data)
    graph = simple_to_nx(data)
    # TODO: any required pre-processing goes here

    if defaults:
        ank_graph_defaults = settings['JSON']['Graph Defaults']
        for (key, val) in ank_graph_defaults.items():
            if key not in graph.graph:
                graph.graph[key] = val

        ank_node_defaults = settings['JSON']['Node Defaults']
        node_defaults = graph.graph.get("node_default", {})
        for (key, val) in node_defaults.items():
            if val == 'False':
                node_defaults[key] = False

        for (key, val) in ank_node_defaults.items():
            if key not in node_defaults or node_defaults[key] == 'None':
                node_defaults[key] = val

        for node in graph:
            for (key, val) in node_defaults.items():
                if key not in graph.node[node]:
                    graph.node[node][key] = val

        ank_edge_defaults = settings['Graphml']['Edge Defaults']
        edge_defaults = graph.graph.get('edge_default', {})
        for (key, val) in ank_edge_defaults.items():
            if key not in edge_defaults or edge_defaults[key] == 'None':
                edge_defaults[key] = val

        for src, dst, data in graph.edges(data=True):
            for key, val in edge_defaults.items():
                if key not in data:
                    data[key] = val

        graph.graph['address_family'] = 'v4'
        graph.graph['enable_routing'] = True

        #TODO: move out of defaults boolean, and try/catch
        for node in sorted(graph):
            graph.node[node]['asn'] = int(graph.node[node]['asn'])

    # TODO: set default x/y if not set - or else json export will do it
    graph.graph['file_type'] = 'json'

    return graph
