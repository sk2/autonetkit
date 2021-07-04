from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TopologyElement:
    _data: Dict = field(default_factory=dict)

class BaseTopology:
    pass
    # _data: Dict = field(default_factory=dict)
