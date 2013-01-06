import networkx as nx

g = nx.read_graphml("nren.graphml")

print set(d['Network'] for n, d in g.nodes(data=True))
for n in g:
    if g.node[n]['Network'] == "OPTOSUNET":
        g.node[n]['asn'] = 1653
    if g.node[n]['Network'] == "MREN":
        g.node[n]['asn'] = 40981 # uni of Montenegro

#mapping = dict((n, "%s__%s" %(d.get('Label'), d.get('Network'))) for n, d in g.nodes(data=True))
#print mapping

#g=nx.relabel_nodes(g,mapping, copy=False)
nx.write_graphml(g, "nren.graphml")
