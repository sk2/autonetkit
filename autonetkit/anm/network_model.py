import time

import autonetkit.log as log
import networkx as nx
from autonetkit.anm.graph import NmGraph

class NetworkModel(object):

    """"""

    def __init__(self, all_multigraph = False):
        """"""

        self.all_multigraph = all_multigraph
        self._overlays = {}
        self.add_overlay('phy')
        self.add_overlay('graphics')

        self.label_seperator = '_'
        self.label_attrs = ['label']
        self._build_node_label()
        self.timestamp = time.strftime('%Y%m%d_%H%M%S',
                                       time.localtime())

        #TODO: make this a proper method

    def __repr__(self):
        """"""

        return 'ANM %s' % self.timestamp

    def __len__(self):
        return len(self._overlays)

    @property
    def overlay_nx_graphs(self):
        """"""

        return self._overlays

    def has_overlay(self, overlay_id):
        """"""

        return overlay_id in self._overlays

    def dump(self):
        import autonetkit.ank_json as ank_json
        data = ank_json.jsonify_anm(self)

        # data = data.replace("\\n", "\n")
        # data = data.replace('\\"', '\"')

        return data

    def save(self):
        """"""

        # TODO: take optional filename as parameter

        import autonetkit.ank_json as ank_json
        import os
        import gzip
        archive_dir = os.path.join('versions', 'anm')
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir)

        data = ank_json.jsonify_anm(self)
        json_file = 'anm_%s.json.gz' % self.timestamp
        json_path = os.path.join(archive_dir, json_file)
        log.debug('Saving to %s' % json_path)
        with gzip.open(json_path, 'wb') as json_fh:
            json_fh.write(data)

    def restore_latest(self, directory=None):
        """Restores latest saved ANM"""

        import os
        import glob
        if not directory:
            directory = os.path.join('versions', 'anm')

        glob_dir = os.path.join(directory, '*.json.gz')
        pickle_files = glob.glob(glob_dir)
        pickle_files = sorted(pickle_files)
        try:
            latest_file = pickle_files[-1]
        except IndexError:

# No files loaded

            log.warning('No previous ANM saved. Please compile new ANM')
            return
        self.restore(latest_file)

    def restore(self, pickle_file):
        """"""

        import json
        import gzip
        import autonetkit.ank_json as ank_json
        log.debug('Restoring %s' % pickle_file)
        with gzip.open(pickle_file, 'r') as filehandle:
            data = json.load(filehandle)
            for (overlay_id, graph_data) in data.items():

                self._overlays[overlay_id] = \
                    ank_json.ank_json_loads(graph_data)

        ank_json.rebind_interfaces(self)

    @property
    def _phy(self):
        """"""

        return NmGraph(self, 'phy')

    def initialise_graph(self, graph):
        """Sets input graph. Converts to undirected.
        Initialises graphics overlay."""
        #TODO: remove this dependency from workflow

        graph = nx.Graph(graph)
        g_graphics = self['graphics']
        g_in = self.add_overlay('input', graph=graph, directed=False)
        g_graphics.add_nodes_from(g_in, retain=[
            'x',
            'y',
            'device_type',
            'device_subtype',
            'pop',
            'label',
            'asn',
        ])
        return g_in

    def add_overlay(
        self,
        name,
        nodes=None,
        graph=None,
        directed=False,
        multi_edge=False,
        retain=None,
    ):
        """Adds overlay graph of name name"""

        multi_edge = multi_edge or self.all_multigraph

        if graph:
            if not directed and graph.is_directed():
                if multi_edge:
                    graph = nx.MultiGraph(graph)
                else:
                    log.info('Converting graph %s to undirected' % name)
                    graph = nx.Graph(graph)
        elif directed:

            if multi_edge:
                graph = nx.MultiDiGraph()
            else:
                graph = nx.DiGraph()
        else:
            if multi_edge:
                graph = nx.MultiGraph()
            else:
                graph = nx.Graph()

        #TODO: revisit this0
        #TODO: warn if name already in use so don't clobber
        self._overlays[name] = graph
        overlay = NmGraph(self, name)
        overlay.allocate_interfaces()
        if nodes:
            retain = retain or []  # default is an empty list
            overlay.add_nodes_from(nodes, retain)

        return overlay

    def __iter__(self):
        return iter(NmGraph(self, name) for name in self.overlays())

    def overlays(self):
        """"""

        return self._overlays.keys()

    def devices(self, *args, **kwargs):
        """"""

        return self._phy.filter(*args, **kwargs)

    def __getitem__(self, key):
        """"""

        return NmGraph(self, key)

    def node_label(self, node):
        """Returns node label from physical graph"""

        return self.default_node_label(node)

    def _build_node_label(self):
        """"""

        def custom_label(node):
            return self.label_seperator.join(str(self._overlays['phy'
                ].node[node.node_id].get(val)) for val in
            self.label_attrs if self._overlays['phy'
            ].node[node.node_id].get(val) is not None)

        self.node_label = custom_label

    def set_node_label(self, seperator, label_attrs):
        """"""

        try:
            label_attrs.lower()
            label_attrs = [label_attrs]  # was a string, put into list
        except AttributeError:
            pass  # already a list

        self.label_seperator = seperator
        self.label_attrs = label_attrs
