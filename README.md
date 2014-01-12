
# AutoNetkit
This is the current development beta.
For more information, including installation instructions and a how-to guide, please see www.autonetkit.org

[![PyPi version](https://pypip.in/v/autonetkit/badge.png)](https://crate.io/packages/autonetkit/)

# About

AutoNetkit is a configuration engine to quickly and easily build large scale network configurations.
The primary focus is on emulated networks, but the framework can be extended to hardware networks.

# Features

## High-level syntax

    g_ospf = anm.add_overlay("ospf")
    g_ospf.add_nodes_from(g_in.routers())
    g_ospf.add_edges_from(e for e in g_in.edges()
        if e.src.asn == e.dst.asn)

## Visualization

AutoNetkit provides real-time feedback on network designs using a [d3.js](http://d3js.org) network rendering engine.
![d3.js based visualization](http://sk2.github.io/autonetkit/img/ank_vis.png)

# Installing

    $ pip install autonetkit

For the visualization:

    $ pip install autonetkit_vis

# Using

Draw a graph in an editor such as yEd, and save in the graphml format.

Examples of topology files can be found in the example directory.

    $ autonetkit -f topology.graphml
    INFO AutoNetkit 0.8.2
    INFO Automatically assigning input interfaces
    INFO Allocating v4 Infrastructure IPs
    INFO Allocating v4 Primary Host loopback IPs
    INFO All IPv4 tests passed.
    INFO All validation tests passed.
    INFO Compile for netkit on localhost
    INFO Compiling Netkit for localhost
    INFO Rendering Network
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


## Visualization
You can start the visualization webserver, and topologies will automatically be sent:

    $ ank_webserver --ank_vis

## Extending
A tutorial on extending using the API can be found [here](http://sk2.github.io/autonetkit/tutorial/extending.html) or as an iPython Notebook  [here](http://sk2.github.io/autonetkit/tutorial/extending.ipynb).


# Users

Users from industry, academia, and university teaching.

# Further information

More information on AutoNetkit:

*  [AutoNetkit YouTube Channel](http://www.youtube.com/autonetkit)
*  [CoNEXT 2013 Slides](https://db.tt/JkRrU5q5) (Dec 13)
*  [PyCon Australia 2013 Presentation on Autonetkit](http://t.co/H4NWROoAJK) [(Slides)](http://t.co/x0NXLMATEq) (July 13)
*  [AutoNetkit website](http://www.autonetkit.org)
*  [API Documentation](https://autonetkit.readthedocs.org/)
*  [CoNext 2013 Conference Paper](http://conferences.sigcomm.org/co-next/2013/program/p235.pdf)

# Contact
*  [Twitter](https://twitter.com/autonetkit)
*  [Mailing list](https://groups.google.com/group/autonetkit)

