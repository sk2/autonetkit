from dataclasses import dataclass
from functools import partial
from typing import TypeVar

N = TypeVar('N', bound='Node')
L = TypeVar('L', bound='Link')
P = TypeVar('P', bound='Port')
NP = TypeVar('NP', bound='NodePath')
PP = TypeVar('PP', bound='PortPath')
T = TypeVar('T', bound='Topology')
NM = TypeVar('NM', bound='NetworkModel')

# TODO: note eq set false so inherit rather than generate own eq and then hash functions
ank_element_dataclass = partial(dataclass, eq=False, repr=False)