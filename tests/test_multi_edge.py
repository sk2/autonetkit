import autonetkit
import autonetkit.log as log

log.info("Testing ANM")

anm = autonetkit.anm.NetworkModel()

g_me = anm.add_overlay("multi", multi_edge = True)
graph = g_me._graph

g_me.add_nodes_from(["r1", "r2", "r3"])
# add two edges
g_me.add_edges_from(([("r1", "r2")]))
g_me.add_edges_from(([("r1", "r2")]))
g_me.add_edges_from(([("r1", "r2")]))
g_me.add_edges_from(([("r1", "r2")]))
g_me.add_edges_from(([("r1", "r2")]))

r1 = g_me.node("r1")

for index, edge in enumerate(r1.edges()):
    #print index, edge
    edge.index = "i_%s" % index

for edge in r1.edges():
    #print edge, edge.index
    pass


"""
e1 = r1.edges()[0]
e1a = g_me.edge(e1)
assert(e1 == e1a)
e2 = r1.edges()[1]
assert(e1 != e2)
#TODO: check why neq != also returns true for e1 != e1a
"""

#print g_me.edge("r1", "r2", 0).index
#print g_me.edge("r1", "r2", 1).index

print "edges"
for edge in g_me.edges():
    print edge

out_of_order = [g_me.edge("r1", "r2", x) for x in [4, 1, 3, 2, 0]]
#print [e.index for e in out_of_order]
in_order = sorted(out_of_order)
#print in_order
#print [e.index for e in in_order]

# test adding to another mutli edge graph
print "adding"
g_me2 = anm.add_overlay("multi2", multi_edge = True)
g_me2.add_nodes_from(g_me)
print "add", len(g_me.edges())
g_me2.add_edges_from(g_me.edges(), retain = "index")
for edge in g_me2.edges():
    print edge, edge.index

# examine underlying nx structure


#print graph
#print type(graph)

for u, v, k in graph.edges(keys=True):
    pass
    #print u, v, k
    #print graph[u][v][k].items()
    #graph[u][v][k]['test'] = 123

from networkx.readwrite import json_graph
import json
data =  json_graph.node_link_data(graph)
with open("multi.json", "w") as fh:
    fh.write(json.dumps(data, indent=2))
