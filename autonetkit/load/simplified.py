from typing import Optional, List, Dict, Tuple

from pydantic import BaseModel

from autonetkit.network_model.types import DeviceType


class SimplifiedNode(BaseModel):
    id: Optional[str]
    label: Optional[str]
    type: Optional[DeviceType]
    x: Optional[int] = 0
    y: Optional[int] = 0
    asn: Optional[int]
    target: Optional[str]
    data: Optional[Dict] = {}


class SimplifiedTopology(BaseModel):
    nodes: List[SimplifiedNode]
    links: Optional[List[Tuple[str, str]]] = []
