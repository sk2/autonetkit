import autonetkit.log as log
from autonetkit.anm.base import OverlayBase


class OverlaySubgraph(OverlayBase):

    """OverlaySubgraph"""

    def __init__(self, anm, overlay_id, graph, name=None):
        """"""

        object.__setattr__(self, '_subgraph_name', name)
        super(OverlaySubgraph, self).__init__(anm, overlay_id)
        self._graph = graph

    def __repr__(self):
        return self._subgraph_name or 'subgraph'
