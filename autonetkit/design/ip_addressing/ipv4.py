            if not interface['ipv4'].is_bound:
                continue
        allocated = list(
            interface.ipv4_address for interface in physical_interfaces
             if interface.is_bound
            and interface['ipv4'].is_bound)
        if all(interface.ipv4_address for interface in
               physical_interfaces if interface.is_bound
               and interface['ipv4'].is_bound):
            # add as a manual allocated device
            manual_alloc_devices.add(device)
            #TODO: make these inverse sets
            allocated += sorted([i for i in node.physical_interfaces()
                                 if i.is_bound and i.ipv4_address])
            unallocated += sorted([i for i in node.physical_interfaces()
                                   if i.is_bound and not i.ipv4_address
                                   and i['ipv4'].is_bound])
