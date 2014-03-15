import autonetkit.log as log
from overlay_base import OverlayBase


class OverlaySubgraph(OverlayBase):

    """OverlaySubgraph"""

    def __init__(
        self,
        anm,
        overlay_id,
        graph,
        name=None,
    ):
        """"""

        super(OverlaySubgraph, self).__init__(anm, overlay_id)
        self._graph = graph
        self._subgraph_name = name

    def __repr__(self):
        return self._subgraph_name or 'subgraph'
