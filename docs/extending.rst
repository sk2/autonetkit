
AutoNetkit API tutorial
=======================

Written for AutoNetkit 0.9

Create Network

.. code:: python

    import autonetkit
    anm = autonetkit.NetworkModel()
.. code:: python

    g_in = anm.add_overlay("input")
    nodes = ['r1', 'r2', 'r3', 'r4', 'r5']
    
    g_in.add_nodes_from(nodes)
    g_in.update(device_type = "router", asn=1)
    g_in.update("r5", asn = 2)
.. code:: python

    positions = {'r1': (10, 79),
     'r2': (226, 25),
     'r3': (172, 295),
     'r4': (334, 187),
     'r5': (496, 349)}
    
    for n in g_in:
        n.x, n.y = positions[n]
    
    autonetkit.update_http(anm)

.. code:: python

    edges = [("r1", "r2"), ("r2", "r4"), ("r1", "r3"), 
             ("r3", "r4"), ("r3", "r5"), ("r4", "r5")]
    g_in.add_edges_from(edges)
    autonetkit.update_http(anm)

.. code:: python

    g_in.allocate_input_interfaces()
    autonetkit.update_http(anm)
.. code:: python

    
    
    
    for node in sorted(g_in):
        print node
        for index, interface in enumerate(node.physical_interfaces()):
            print interface
            interface.name = "eth%s" % index
            
        print node
    autonetkit.update_http(anm)
.. code:: python

    g_phy = anm['phy']
    g_phy.add_nodes_from(g_in, retain=["asn", "device_type", "x", "y"])
    g_phy.update(use_ipv4 = True, host = "localhost", platform = "netkit", syntax = "quagga")
    
    g_phy.add_edges_from(g_in.edges())
    autonetkit.update_http(anm)

.. code:: python

    g_ospf = anm.add_overlay("ospf")
    g_ospf.add_nodes_from(g_in.routers())
    g_ospf.add_edges_from(e for e in g_in.edges()
                          if e.src.asn == e.dst.asn)
    autonetkit.update_http(anm) 
.. code:: python

    for node in g_ospf:
        for interface in node.physical_interfaces():
            interface.cost = 10
    autonetkit.update_http(anm)
.. code:: python

    g_ebgp = anm.add_overlay("ebgp_v4", directed = True)
    g_ebgp.add_nodes_from(g_in.routers())
    edges = [e for e in g_in.edges()
             if e.src.asn != e.dst.asn]
    # Add in both directions
    g_ebgp.add_edges_from(edges, bidirectional = True)
    autonetkit.update_http(anm)              

.. code:: python

    g_ibgp = anm.add_overlay("ibgp_v4", directed = True)
    g_ibgp.add_nodes_from(g_in.routers())
    edges = [(s,t) for s in g_ibgp for t in g_ibgp
             # belong to same ASN, but not self-loops
             if s != t and s.asn == t.asn]
    
    # Add in both directions
    g_ibgp.add_edges_from(edges, bidirectional = True)
    autonetkit.update_http(anm)

.. code:: python

    import autonetkit.ank as ank_utils
    g_ipv4 = anm.add_overlay("ipv4")
    g_ipv4.add_nodes_from(g_in)
    g_ipv4.add_edges_from(g_in.edges())
    
    # Split the point-to-point edges to add a collision domain
    edges_to_split = [edge for edge in g_ipv4.edges()
                if edge.src.is_l3device() and edge.dst.is_l3device()]
    for edge in edges_to_split:
        edge.split = True  # mark as split for use in building nidb
        
    split_created_nodes = list(ank_utils.split(g_ipv4, edges_to_split,
        retain=['split'], id_prepend='bc'))
    
    for node in split_created_nodes:
        # Set the co-ordinates using 'x', 'y' of g_in
        # based on neighbors in g_ipv4
        node.x = ank_utils.neigh_average(g_ipv4, node, 'x', g_in)
        node.y = ank_utils.neigh_average(g_ipv4, node, 'y', g_in)
        # Set most frequent of asn property in g_phy
        # ASN is used to allocate IPs
        node.asn = ank_utils.neigh_most_frequent(g_ipv4, node,
                                                 'asn', g_phy)
        node.broadcast_domain = True
        node.device_type = "broadcast_domain"
        
    autonetkit.update_http(anm)
.. code:: python

    # Now use allocation plugin
    import autonetkit.plugins.ipv4 as ipv4
    ipv4.allocate_infra(g_ipv4)
    ipv4.allocate_loopbacks(g_ipv4)
    
    autonetkit.update_http(anm)
.. code:: python

    # Now construct NIDB
    nidb = autonetkit.DeviceModel()
    # NIDB is separate to the ANM -> copy over more properties
    retain = ['label', 'host', 'platform', 'x', 'y', 'asn', 'device_type']
    nidb.add_nodes_from(g_phy, retain=retain)
    
    # Usually have a base g_ip which has structure
    # allocate to g_ipv4, g_ipv6
    retain.append("subnet") # also copy across subnet
    nidb.add_nodes_from(g_ipv4.nodes("broadcast_domain"), retain=retain)
    nidb.add_edges_from(g_ipv4.edges())
    
    # Also need to copy across the collision domains
    
    autonetkit.update_http(anm, nidb)
.. code:: python

    anm.add_overlay("ipv6")
    anm.add_overlay("bgp")
    autonetkit.update_http(anm)
.. code:: python

    import autonetkit.compilers.platform.netkit as pl_netkit
    host = "localhost"
    
    platform_compiler = pl_netkit.NetkitCompiler(nidb, anm, host)
    platform_compiler.compile() 
.. code:: python

    import autonetkit.render
    autonetkit.render.render(nidb)

The output files are put

::

    into rendered/localhost/netkit

For instance:

::

    ├── lab.conf
    ├── r1
    │   ├── etc
    │   │   ├── hostname
    │   │   ├── shadow
    │   │   ├── ssh
    │   │   │   └── sshd_config
    │   │   └── zebra
    │   │       ├── bgpd.conf
    │   │       ├── daemons
    │   │       ├── isisd.conf
    │   │       ├── motd.txt
    │   │       ├── ospfd.conf
    │   │       └── zebra.conf
    │   └── root
    ├── r1.startup
    ├── r2
    │   ├── etc
    │   │   ├── hostname
    │   │   ├── shadow
    │   │   ├── ssh
    │   │   │   └── sshd_config
    │   │   └── zebra
    │   │       ├── bgpd.conf
    │   │       ├── daemons
    │   │       ├── isisd.conf
    │   │       ├── motd.txt
    │   │       ├── ospfd.conf
    │   │       └── zebra.conf
    │   └── root
    ├── r2.startup

Can also write our own compiler and templates:

.. code:: python

    # AutoNetkit renderer expects filenames for templates
    # uses the Mako template format
    router_template_str = """Router |||rendered on ${date} by ${version_banner}
    % for interface in node.interfaces:
    interface ${interface.id}
        description ${interface.description}
        ip address ${interface.ipv4_address} netmask ${interface.ipv4_netmask}
    % endfor
    !
    router ospf ${node.ospf.process_id}
        % for link in node.ospf.ospf_links:
        network ${link.network.cidr} area ${link.area}
        % endfor
    !
    router bgp ${node.asn}
    % for neigh in node.bgp.ibgp_neighbors:
      ! ${neigh.neighbor}
      neighbor ${neigh.loopback} remote-as ${neigh.asn}
      neighbor ${neigh.loopback} update-source ${node.loopback_zero.ipv4_address}
      neighbor ${neigh.loopback} next-hop-self
    % endfor
    !
    % for neigh in node.bgp.ebgp_neighbors:
      ! ${neigh.neighbor}
      neighbor ${neigh.dst_int_ip} remote-as ${neigh.asn}
      neighbor ${neigh.dst_int_ip} update-source ${neigh.local_int_ip}
    % endfor
    !    
    """
    
    router_template = "router.mako"
    with open(router_template, "w") as fh:
        fh.write(router_template_str)
.. code:: python

    from autonetkit.compilers.device import router_base
    
    from autonetkit.nidb.config_stanza import ConfigStanza as ConfigStanza
    
    class simple_router_compiler(router_base.RouterCompiler):
        lo_interface = 'lo:1'
        
        def compile(self, node):
            self.interfaces(node)
            self.ospf(node)
            self.bgp(node)
    
        def interfaces(self, node):
            # Append attributes to the interface, rather than add a stanza
            ipv4_node = self.anm['ipv4'].node(node)
            if node.is_l3device:
                node.loopback_zero.id = self.lo_interface
                node.loopback_zero.description = 'Loopback'
                node.loopback_zero.ipv4_address = ipv4_node.loopback
                node.loopback_zero.ipv4_netmask = "255.255.255.255" 
            #interface_list.append(stanza)
    
            for interface in node.physical_interfaces():
                ipv4_int = ipv4_node.interface(interface)
                interface.ipv4_address = ipv4_int.ip_address
                interface.ipv4_netmask = ipv4_int.subnet.netmask
                                                                        
        def ospf(self, node):
            node.add_stanza("ospf", process_id = 1)
            ospf_links = []
            for interface in node.physical_interfaces():
                ipv4_int = self.anm['ipv4'].interface(interface)
                ospf_links.append(ConfigStanza(network=ipv4_int.subnet,
                                                area=0))
            node.ospf.ospf_links = ospf_links
        
        def bgp(self, node):
            node.add_stanza("bgp")
            g_ebgp = self.anm["ebgp_v4"]
            ebgp_neighbors = []
            ibgp_neighbors = []
            for session in g_ebgp.edges(node):
                neighbor = session.dst # remote node
                stanza = ConfigStanza(neighbor = neighbor,
                                       asn = neighbor.asn)
                # Can obtain the dst int, as created bgp session
                # from physical links
                stanza.local_int_ip = session.src_int['ipv4'].ip_address
                stanza.dst_int_ip = session.dst_int['ipv4'].ip_address
                ebgp_neighbors.append(stanza)
                
            for session in g_ibgp.edges(node):
                neighbor = session.dst # remote node
                stanza = ConfigStanza(neighbor = neighbor,
                                       asn = neighbor.asn)
                stanza.loopback = neighbor['ipv4'].loopback
                ibgp_neighbors.append(stanza)
                
            node.bgp.ebgp_neighbors = sorted(ebgp_neighbors, key = lambda x: x.neighbor)
            node.bgp.ibgp_neighbors = sorted(ibgp_neighbors, key = lambda x: x.neighbor)

.. code:: python

    
    topology_template_str = """Topology rendered on ${date} by ${version_banner}
    % for host in topology.hosts:
    host: ${host}
    % endfor
    """
    
    topology_template = "topology.mako"
    with open(topology_template, "w") as fh:
        fh.write(topology_template_str)
.. code:: python

    from autonetkit.compilers.platform import platform_base
    import netaddr
    from autonetkit.nidb import config_stanza
    
    class simple_platform_compiler(platform_base.PlatformCompiler):
        def compile(self):        
            rtr_comp = simple_router_compiler(self.nidb, self.anm)
            
            for node in nidb.routers(host=host):
                for index, interface in enumerate(node.physical_interfaces()):
                    interface.id = "eth%s" % index
                
                # specify router template
                node.add_stanza("render")
                node.render.template = router_template
                node.render.dst_folder = "rendered"
                node.render.dst_file = "%s.conf" % node
                
                # enable rendering for node
                node.do_render = True
                # and compile
                rtr_comp.compile(node)   
                              
            # and the topology
            lab_topology = self.nidb.topology(self.host)
            # template settings for the renderer
            lab_topology.render_template = topology_template
            lab_topology.render_dst_folder = "rendered"
            lab_topology.render_dst_file = "lab.conf"
            
            lab_topology.hosts = []
            for node in nidb.routers(host=host):
                lab_topology.hosts.append(node)

.. code:: python

    # Now construct NIDB
    nidb = autonetkit.DeviceModel()
    # NIDB is separate to the ANM -> copy over more properties
    retain = ['label', 'host', 'platform', 'x', 'y', 'asn', 'device_type']
    nidb.add_nodes_from(g_phy, retain=retain)
    
    # Usually have a base g_ip which has structure
    # allocate to g_ipv4, g_ipv6
    retain.append("subnet") # also copy across subnet
    nidb.add_nodes_from(g_ipv4.nodes("broadcast_domain"), retain=retain)
    nidb.add_edges_from(g_ipv4.edges())
    
    # Also need to copy across the collision domains
    
    autonetkit.update_http(anm, nidb)
.. code:: python

    sim_plat = simple_platform_compiler(nidb, anm, "localhost")
    sim_plat.compile()
    autonetkit.update_http(anm, nidb)
.. code:: python

    for node in nidb:
        print node.dump()
.. code:: python

    import autonetkit.render
    autonetkit.render.render(nidb)
.. code:: python

    with open("rendered/lab.conf") as fh:
        print fh.read()
.. code:: python

    with open("rendered/r1.conf") as fh:
        print fh.read()
.. code:: python

    with open("rendered/r5.conf") as fh:
        print fh.read()

