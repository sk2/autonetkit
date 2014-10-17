        physical_interfaces = list(device.physical_interfaces())
        allocated = list(
            interface.ipv6_address for interface in physical_interfaces
            if interface.is_bound and interface['ipv6'].is_bound)

        if all(interface.ipv6_address for interface in
               physical_interfaces if interface.is_bound
               and interface['ipv6'].is_bound):

            # add as a manual allocated device
            manual_alloc_devices.add(device)
            allocated += sorted([i for i in node.physical_interfaces()
                                 if i.is_bound and i.ipv6_address])
            unallocated += sorted([i for i in node.physical_interfaces()
                                   if i.is_bound and not i.ipv6_address
                                   and i['ipv6'].is_bound])
