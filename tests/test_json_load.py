#!/usr/bin/python
# -*- coding: utf-8 -*-
import autonetkit
from autonetkit.load.load_json import simple_to_nx, nx_to_simple

house = autonetkit.example.house()
data = house['phy']._graph
s1 = nx_to_simple(data)

with open("house.json", "w") as fh:
    import json
    fh.write(json.dumps(s1, sort_keys=True, indent=2))

nx1 = simple_to_nx(s1)
s2 = nx_to_simple(nx1)
nx2 = simple_to_nx(s2)

graph = nx2
print graph.nodes(data=True)
print graph.edges(data=True)

