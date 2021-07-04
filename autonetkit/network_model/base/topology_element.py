from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TopologyElement:
    _data: Dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

@dataclass
class BaseTopology:
    pass
    # _data: Dict = field(default_factory=dict)
