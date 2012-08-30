def network_hostname(node):
    print node.dump()
    print "%s_%s" % (node.Network, node.label)
    return "%s_%s" % (node.Network, node.label)
