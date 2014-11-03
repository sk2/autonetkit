import autonetkit.console_script as console_script
import os
import autonetkit
import autonetkit.load.graphml as graphml
import autonetkit.diff

automated = True # whether to open ksdiff, log to file...
enabled = False
if __name__ == "__main__":
     # not called by test
    automated = False
    enabled = True



remote_server = "54.252.205.75"

if enabled:
    dirname, filename = os.path.split(os.path.abspath(__file__))

    input_file = os.path.join(dirname, "../big.graphml")
    input_graph = graphml.load_graphml(input_file)

    import autonetkit.build_network as build_network
    anm = build_network.initialise(input_graph)
    anm = build_network.apply_design_rules(anm)

    render_hostname = "localhost"

    nidb = console_script.create_nidb(anm)
    import autonetkit.compilers.platform.netkit as pl_netkit
    nk_compiler = pl_netkit.NetkitCompiler(nidb, anm, render_hostname)
    nk_compiler.compile()

    import autonetkit.render
    autonetkit.render.render(nidb)

    import autonetkit.deploy.netkit as nk_deploy
    username = "ubuntu"
    home_dir = os.path.expanduser("~")
    key_filename = os.path.join(home_dir, ".ssh/aws.pem")
    dst_folder = nidb.topology['localhost'].render_dst_folder
    nk_deploy.deploy(remote_server, username, dst_folder,
    	key_filename, parallel_count = 10)

    #console_script.measure_network(anm, nidb)
