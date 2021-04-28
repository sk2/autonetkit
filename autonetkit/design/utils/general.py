import statistics

import typing
from collections import defaultdict

if typing.TYPE_CHECKING:
    from autonetkit.network_model.node import Node


def move_to_average_peer_locations(node: 'Node') -> None:
    """

    @param node:
    """
    all_x = [n.get("x") for n in node.peer_nodes() if n.get("x") is not None]
    all_y = [n.get("y") for n in node.peer_nodes() if n.get("y") is not None]
    if len(all_x) and len(all_y):
        mean_x = statistics.mean(all_x)
        mean_y = statistics.mean(all_y)
    else:
        mean_x = mean_y = None
    node.set("x", mean_x)
    node.set("y", mean_y)


def group_by(nodes: typing.List['Node'], key: str) -> typing.Dict[str, typing.List['Node']]:
    """

    @param nodes:
    @param key:
    @return:
    """
    result = defaultdict(list)
    for node in nodes:
        result[node.get(key)].append(node)

    return dict(result)
