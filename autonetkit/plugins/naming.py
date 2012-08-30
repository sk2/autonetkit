import autonetkit.ank as ank

def network_hostname(node):
    network = node.Network
    if network:
        return "%s_%s" % (ank.name_folder_safe(network), 
                ank.name_folder_safe(node.label))
    else:
        return ank.name_folder_safe(node.label) 
