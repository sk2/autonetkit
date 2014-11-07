def initialize(filename, defaults = True):
    from autonetkit.build_network import load, initialise
    with open(filename) as fh:
        data = fh.read()

    graph = load(data, defaults=defaults)
    anm = initialise(graph)
    return anm