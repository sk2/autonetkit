import typing

from autonetkit.network_model.link import Link
from autonetkit.network_model.node import Node
from autonetkit.network_model.path import NodePath, PortPath
from autonetkit.network_model.port import Port

N = typing.TypeVar('N', bound=Node)
L = typing.TypeVar('L', bound=Link)
P = typing.TypeVar('P', bound=Port)
NP = typing.TypeVar('NP', bound=NodePath)
PP = typing.TypeVar('PP', bound=PortPath)


