import sys


def convert():
    filename = sys.argv[1]
    with open(filename, "r") as fh:
        data = fh.read()

    from autonetkit.build_network import build, load
    graph = load(data)
    anm = build(graph)


    import autonetkit
    g_in_nx = anm['input']._graph

    output = autonetkit.load.load_json.nx_to_simple(g_in_nx)

if __name__ == "__main__":
    main()