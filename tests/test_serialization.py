import autonetkit
import os
import autonetkit.load.graphml as graphml
import shutil

def test():


    automated = True # whether to open ksdiff, log to file...
    if __name__ == "__main__":
        automated = False

    dirname, filename = os.path.split(os.path.abspath(__file__))

    anm =  autonetkit.NetworkModel()
    input_file = os.path.join(dirname, "small_internet.graphml")
    input_graph = graphml.load_graphml(input_file)

    import autonetkit.build_network as build_network
    anm = build_network.initialise(input_graph)
    anm = build_network.apply_design_rules(anm)
    anm.save()
    anm_restored =  autonetkit.NetworkModel()
    anm_restored.restore_latest()
    g_phy_original = anm['phy']
    g_phy_restored = anm_restored['phy']
    assert(all(n in g_phy_restored for n in g_phy_original))

    #TODO: do more extensive deep check of parameters

    import autonetkit.workflow as workflow
    render_hostname = "localhost"

    nidb = workflow.create_nidb(anm)
    import autonetkit.compilers.platform.netkit as pl_netkit
    nk_compiler = pl_netkit.NetkitCompiler(nidb, anm, render_hostname)
    nk_compiler.compile()

    nidb.save()
    nidb_restored =  autonetkit.DeviceModel()
    nidb_restored.restore_latest()
    assert(all(n in nidb_restored for n in nidb))

    # cleanup
    shutil.rmtree("versions")
