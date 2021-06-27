from enum import Enum
from typing import NewType

TopologyId = NewType('TopologyId', str)
NodeId = NewType('NodeId', str)
LinkId = NewType('LinkId', str)
PortId = NewType('PortId', str)
PathId = NewType('PathId', str)


class DeviceType(Enum):
    ROUTER = "Router"
    SWITCH = "Switch"
    HOST = "Host"
    VIRTUAL = "Virtual"
    BROADCAST_DOMAIN = "Broadcast Domain"


LAYER3_DEVICES = {DeviceType.ROUTER, DeviceType.HOST}


class PortType(Enum):
    PHYSICAL = "Physical"
    LOGICAL = "Logical"
