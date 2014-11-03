class NmGraphData(object):

    """API to access link in network"""

    def __init__(self, anm, overlay_id):

        # Set using this method to bypass __setattr__

        object.__setattr__(self, 'anm', anm)
        object.__setattr__(self, 'overlay_id', overlay_id)

    def __repr__(self):
        """"""

        return 'Data for (%s, %s)' % (self.anm, self.overlay_id)

    def dump(self):
        """"""

        print str(self._graph.graph)

    @property
    def _graph(self):

        # access underlying graph for this NmNode

        return self.anm.overlay_nx_graphs[self.overlay_id]

    def __getattr__(self, key):
        return self._graph.graph.get(key)

    def __setattr__(self, key, val):
        self._graph.graph[key] = val

    def __getitem__(self, key):
        """"""

        return self._graph.graph.get(key)

    def __setitem__(self, key, val):
        """"""

        self._graph.graph[key] = val
