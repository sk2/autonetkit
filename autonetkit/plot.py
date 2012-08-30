import networkx as nx

def plot_dot(overlay_graph, edge_label_attribute = None, save = True, show = False):
    #TODO: turn off rescaling
    import subprocess
    graph = overlay_graph._graph.copy()
    graph_name = overlay_graph.name

    graph = graph.to_undirected()

    for node in overlay_graph:
        graph.node[node.node_id]['label'] = node.overlay.graphics.label
        (x, y) = node.overlay.graphics.x, node.overlay.graphics.y
        (x, y) = x/4, -1*y/4
        graph.node[node.node_id]['pos'] = "%s,%s" % (x, y)
        graph.node[node.node_id]['image'] = "icons/%s.png" % node.overlay.graphics.device_type
        graph.node[node.node_id]['shape'] = 'none'
        graph.node[node.node_id]['fontsize'] = 25
        graph.node[node.node_id]['labelloc'] = 'b' 
        graph.node[node.node_id]['fontcolor'] = 'white' 

    filename = "%s.dot" % graph_name
    nx.to_dot(graph, filename) 
    cmd = ["dot", "-Kfdp", filename, "-Tpdf", "-o", "%s.pdf" % graph_name]
    subprocess.call(cmd)

def plot_pylab(overlay_graph, edge_label_attribute = None, node_label_attribute = None, save = True, show = False):
    """ Plot a graph"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print ("Matplotlib not found, not plotting using Matplotlib")
        return
    graph = overlay_graph._graph
    graph_name = overlay_graph.name

    try:
        import numpy
    except ImportError:
        print("Matplotlib plotting requires numpy for graph layout")
        return
    
    try:
        ids, x, y = zip(*[(node.id , node.overlay.graphics.x, node.overlay.graphics.y)
                for node in overlay_graph])
        x = numpy.asarray(x, dtype=float)
        y = numpy.asarray(y, dtype=float)
#TODO: combine these two operations together
        x -= x.min()
        x *= 1.0/x.max() 
        y -= y.min()
        y *= -1.0/y.max() # invert
        y += 1 # rescale from 0->1 not 1->0
#TODO: see if can use reshape-type commands here
        co_ords = zip(list(x), list(y))
        co_ords = [numpy.array([x, y]) for x, y in co_ords]
        pos = dict( zip(ids, co_ords))
    except KeyError:
        pos=nx.spring_layout(graph)

    plt.clf()
    cf = plt.gcf()
    ax=cf.add_axes((0,0,1,1))
    # Create axes to allow adding of text relative to map
    ax.set_axis_off() 
    font_color = "k"
    node_color = "#336699"
    edge_color = "#888888"

    nodes = nx.draw_networkx_nodes(graph, pos, 
                           node_size = 50, 
                           alpha = 0.8, linewidths = (0,0),
                           node_color = node_color,
                           cmap=plt.cm.jet)

    nx.draw_networkx_edges(graph, pos, arrows=False,
                           edge_color=edge_color,
                           alpha=0.8)
    
    if edge_label_attribute:
        edge_labels = {}
        for edge in overlay_graph.edges():
            attr = edge.get(edge_label_attribute)
            if attr:
                label = "%s" % attr
            else:
                label = ""

            edge_labels[(edge.src.node_id, edge.dst.node_id)] = label
        nx.draw_networkx_edge_labels(graph, pos, 
                            edge_labels = edge_labels,
                            font_size = 10,
                            font_color = font_color)

#TODO: where is anm from here? global? :/
    if node_label_attribute:
        labels = {}
        for n in overlay_graph:
            attr = n.get(node_label_attribute)
            if attr:
                label = "%s\n%s" % (n, attr)
            else:
                label = n

            labels[n.node_id] = label
    else:
        labels = dict( (n.node_id, n) for n in overlay_graph)

#TODO: need to strip out 
    nx.draw_networkx_labels(graph, pos, 
                            labels=labels,
                            font_size = 12,
                            font_color = font_color)

    title = "%s graph" % graph_name
    ax.text(0.02, 0.98, title, horizontalalignment='left',
                            weight='heavy', fontsize=16, color='k',
                            verticalalignment='top', 
                            transform=ax.transAxes)
    if show:
        plt.show()
    if save:
        filename = "%s.pdf" % graph_name
        plt.savefig(filename)

    plt.close()

