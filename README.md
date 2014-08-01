# AutoNetkit

AutoNetkit is a configuration engine to quickly and easily build large-scale network configurations.

![Flowchart](http://sk2.github.io/autonetkit/img/flowchart.png)

[![PyPi version](https://pypip.in/v/autonetkit/badge.png)](https://crate.io/packages/autonetkit/)

# Features

## High-level syntax

    g_ospf = anm.add_overlay("ospf")
    g_ospf.add_nodes_from(g_in.routers())
    g_ospf.add_edges_from(e for e in g_in.edges() if e.src.asn == e.dst.asn)

## Visualization

AutoNetkit provides real-time feedback on network designs using a [d3.js](http://d3js.org) network rendering engine.
![d3.js based visualization](http://sk2.github.io/autonetkit/img/ank_vis.png)

# Installing

    $ pip install autonetkit

For the visualization:

    $ pip install autonetkit_vis

# Using

AutoNetkit 0.9 allows for JSON input. An example JSON input is:

```JSON
{
    "directed": false, "graph": [], "multigraph": false,
    "links": [
    {"dst": "r2", "dst_port": "eth0", "src": "r1", "src_port": "eth0"},
    {"dst": "r3", "dst_port": "eth0", "src": "r1", "src_port": "eth1"},
    {"dst": "r3", "dst_port": "eth1", "src": "r2", "src_port": "eth1"},
    {"dst": "r2", "dst_port": "eth2", "src": "r4", "src_port": "eth0"},
    {"dst": "r5", "dst_port": "eth0", "src": "r4", "src_port": "eth1"},
    {"dst": "r3", "dst_port": "eth2", "src": "r5", "src_port": "eth1"}
    ],
    "nodes": [
    {
        "asn": 1, "device_type": "router", "id": "r1", "x": 350, "y": 400,
        "ports": [
        {"category": "loopback", "description": null, "id": "Loopback0"},
        {"category": "physical", "description": "r1 to r2", "id": "eth0"},
        {"category": "physical", "description": "r1 to r3", "id": "eth1"}
        ]
    },
    {
        "asn": 1, "device_type": "router", "id": "r2", "x": 500, "y": 300,
        "ports": [
        {"category": "loopback", "description": null, "id": "Loopback0"},
        {"category": "physical", "description": "r2 to r1", "id": "eth0"},
        {"category": "physical", "description": "r2 to r3", "id": "eth1"},
        {"category": "physical", "description": "r2 to r4", "id": "eth2"}
        ]
    },
    {
        "asn": 1, "device_type": "router", "id": "r3", "x": 500, "y": 500,
        "ports": [
        {"category": "loopback", "description": null, "id": "Loopback0"},
        {"category": "physical", "description": "r3 to r1", "id": "eth0"},
        {"category": "physical", "description": "r3 to r2", "id": "eth1"},
        {"category": "physical", "description": "r3 to r5", "id": "eth2"}
        ]
    },
    {
        "asn": 2, "device_type": "router", "id": "r4", "x": 675, "y": 300,
        "ports": [
        {"category": "loopback", "description": null, "id": "Loopback0"},
        {"category": "physical", "description": "r4 to r2", "id": "eth0"},
        {"category": "physical", "description": "r4 to r5", "id": "eth1"}
        ]
    },
    {
        "asn": 2, "device_type": "router", "id": "r5", "x": 675, "y": 500,
        "ports": [
        {"category": "loopback", "description": null, "id": "Loopback0"},
        {"category": "physical", "description": "r5 to r4", "id": "eth0"},
        {"category": "physical", "description": "r5 to r3", "id": "eth1"}
        ]
    }
    ]
}
```

Examples of topology files can be found in the example directory.

    $ autonetkit -f example/house.json
    INFO AutoNetkit 0.9.0
    INFO IPv4 allocations: Infrastructure: 10.0.0.0/8, Loopback: 192.168.0.0/22
    INFO Allocating v4 Infrastructure IPs
    INFO Allocating v4 Primary Host loopback IPs
    INFO Skipping iBGP for iBGP disabled nodes: []
    INFO All validation tests passed.
    INFO Rendering Configuration Files
    INFO Finished


This will generate Quagga configurations and Netkit topology files.:

    $ tree rendered/localhost/netkit/
    rendered/localhost/netkit/
    ├── lab.conf
    ├── r1_1
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
    ├── r1_1.startup
    ...

and an example of the resulting configuration file:

    $ rendered/localhost/netkit/r1/etc/zebra/ospfd.conf
    hostname r1
    password 1234
    banner motd file /etc/quagga/motd.txt
    !
      interface eth0
      #Link to to r2
      ip ospf cost 1
      !
      interface eth1
      #Link to to r3
      ip ospf cost 1
      !
    !
    router ospf
      network 10.0.0.0/30 area 0
      network 10.0.0.4/30 area 0
      !
      !
      network 192.168.0.1/32 area 0
    !



## Visualization
You can start the visualization webserver, and topologies will automatically be sent:

    $ ank_webserver --ank_vis

An example of the visualization output for the above JSON house example:

Physical topology:

![phy](http://sk2.github.io/autonetkit/json_house/phy.png)

Physical topology with interfaces:

![phy interfaces](http://sk2.github.io/autonetkit/json_house/phy_int.png)


IPv4 topology:

![ipv4](http://sk2.github.io/autonetkit/json_house/ipv4.png)

OSPF topology:

![ospf](http://sk2.github.io/autonetkit/json_house/ospf.png)

iBGP topology:

![ibgp](http://sk2.github.io/autonetkit/json_house/ibgp.png)

eBGP topology:

![ebgp](http://sk2.github.io/autonetkit/json_house/ebgp.png)


## Extending
A tutorial on extending using the API can be found [here](http://sk2.github.io/autonetkit/tutorial/extending.html) or as an iPython Notebook  [here](http://sk2.github.io/autonetkit/tutorial/extending.ipynb).


# Users

Users from industry, academia, and university teaching.

# Further information

More information on AutoNetkit:

*  [AutoNetkit YouTube Channel](http://www.youtube.com/autonetkit)
*  [CoNEXT 2013 Slides](https://db.tt/JkRrU5q5) (Dec 13)
*  [CoNext 2013 Conference Paper](http://conferences.sigcomm.org/co-next/2013/program/p235.pdf)
*  [Extended recording of CoNext Slides](https://www.youtube.com/watch?v=0W73HLdlwOs)
*  [PyCon Australia 2013 Presentation on Autonetkit](http://t.co/H4NWROoAJK) [(Slides)](http://t.co/x0NXLMATEq) (July 13)

*  [API Documentation](https://autonetkit.readthedocs.org/)
*  [AutoNetkit website](http://www.autonetkit.org)

# Contact
*  [Twitter](https://twitter.com/autonetkit)
*  [Mailing list](https://groups.google.com/group/autonetkit)

