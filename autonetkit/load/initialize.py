def initialize(filename):
    from autonetkit.build_network import load, initialise
    with open(filename) as fh:
        data = fh.read()

    graph = load(data)
    anm = initialise(graph)
    return anm