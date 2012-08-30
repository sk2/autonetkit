import autonetkit.ank as ank

def network_hostname(node):
    network = node.Network or ""
    return "%s_%s" % (ank.name_folder_safe(network), 
            ank.name_folder_safe(node.label))
