from typing import List, Optional, Dict

from pydantic import BaseModel

from autonetkit.network_model.types import DeviceType, PortType, LinkId, PortId, NodeId


class StructuredPort(BaseModel):
    id: Optional[PortId]
    slot: Optional[int]
    type: PortType
    label: Optional[str]
    data: Optional[Dict] = {}
    loopback_zero: Optional[bool]


class StructuredNode(BaseModel):
    id: Optional[NodeId]
    type: Optional[DeviceType]
    label: str
    x: Optional[float]
    y: Optional[float]
    asn: Optional[int]
    target: Optional[int]
    loopback_zero_id: Optional[StructuredPort]
    data: Optional[Dict] = {}
    ports: List[StructuredPort] = []


class StructuredLink(BaseModel):
    id: Optional[LinkId]
    n1: str
    n2: str
    p1: int
    p2: int
    data: Optional[Dict] = {}


class StructuredTopology(BaseModel):
    nodes: List[StructuredNode] = []
    links: List[StructuredLink] = []
