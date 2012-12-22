import ank
import itertools
import netaddr
import os
import pprint
from collections import defaultdict
import string
from datetime import datetime
import autonetkit.log as log
import autonetkit.plugins.naming as naming
import autonetkit.config
settings = autonetkit.config.settings
from ank_utils import alphabetical_sort as alpha_sort

#TODO: rename compiler to build

#TODO: tidy up the dict to list, and sorting formats
#TODO: don't pass lists/dictionaries around: set directly, and then sort in-place later if needed

def dot_to_underscore(instring):
    return instring.replace(".", "_")

class RouterCompiler(object):
    lo_interface = "lo0" #make this clear distinction between interface id and lo IP
# and set per platform

    """Base Router compiler"""
    def __init__(self, nidb, anm):
        self.nidb = nidb
        self.anm = anm

    def compile(self, node):
        phy_node = self.anm['phy'].node(node)
        ip_node = self.anm.overlay.ip.node(node)
        node.label = naming.network_hostname(phy_node)
        node.input_label = phy_node.id
        node.loopback = ip_node.loopback
        node.loopback_subnet = netaddr.IPNetwork(node.loopback)
        node.loopback_subnet.prefixlen = 32
        self.interfaces(node)
        if node in self.anm['ospf']:
            self.ospf(node)

        if node in self.anm['bgp']:
            self.bgp(node)

    def interfaces(self, node):
        phy_node = self.anm.overlay.phy.node(node)
        G_ip = self.anm.overlay.ip
        node.interfaces = []
        for link in phy_node.edges():
            ip_link = G_ip.edge(link)
            nidb_edge = self.nidb.edge(link)
            #TODO: what if multiple ospf costs for this link
            if not ip_link:
                #TODO: fix this
                continue

            subnet =  ip_link.dst.subnet # netmask comes from collision domain on the link
            node.interfaces.append(
                    _edge_id = link.edge_id, # used if need to append
                    id = nidb_edge.id,
                    description = "%s to %s" % (link.src, link.dst),
                    ip_address = link.overlay.ip.ip_address,
                    subnet = subnet,
                    physical = True,
                    )

        node.interfaces.sort("id")
    
    def ospf(self, node):
        """Returns OSPF links, also sets process_id
        """
        G_ospf = self.anm['ospf']
        G_ip = self.anm['ip']

        node.ospf.loopback_area = G_ospf.node(node).area

        phy_node = self.anm['phy'].node(node)
        node.ospf.process_id = 1
        node.ospf.lo_interface = self.lo_interface 
        node.ospf.ospf_links = []
        added_networks = set()
        for link in G_ospf.edges(phy_node):
            ip_link = G_ip.edge(link)
            if not ip_link:
                #TODO: fix this: due to multi edges from router to same switch cluster
                continue
            network = ip_link.dst.subnet,
            if network not in added_networks: # don't add more than once
                added_networks.add(network)
                node.ospf.ospf_links.append(
                    network = ip_link.dst.subnet,
                    area = link.area,
                    )
            

    def bgp(self, node):
        phy_node = self.anm['phy'].node(node)
        G_bgp = self.anm['bgp']
        G_ip = self.anm['ip']
        asn = phy_node.asn # easy reference for cleaner code
        node.asn = asn
        node.bgp.advertise_subnets = G_ip.data.infra_blocks.get(asn) or [] # note: could be none (if single-node AS) - default to empty list
        
        node.bgp.ibgp_neighbors = []
        node.bgp.ibgp_rr_clients = []
        node.bgp.ibgp_rr_parents = []
        node.bgp.ebgp_neighbors = []

        for session in G_bgp.edges(phy_node):
            neigh = session.dst
            neigh_ip = G_ip.node(neigh)
            if session.type == "ibgp":
                data = {
                    'neighbor': neigh.label,
                    'asn': neigh.asn,
                    'loopback': neigh_ip.loopback,
                    'update_source': "loopback 0", #TODO: this is platform dependent???
                    }
                if session.direction == 'down':
                    #ibgp_rr_clients[key] = data
                    node.bgp.ibgp_rr_clients.append(data)
                elif session.direction == 'up':
                    node.bgp.ibgp_rr_parents.append(data)
                else:
                    node.bgp.ibgp_neighbors.append(data)
            else:
                #TODO: fix this: this is a workaround for Quagga next-hop denied for loopback (even with static route)
                ip_link = G_ip.edge(session)
                dst_int_ip = G_ip.edges(ip_link.dst, neigh).next().ip_address #TODO: split this to a helper function
                node.bgp.ebgp_neighbors.append( {
                    'neighbor': neigh.label,
                    'asn': neigh.asn,
                    'loopback': neigh_ip.loopback,
                    'local_int_ip': ip_link.ip_address,
                    'dst_int_ip': dst_int_ip,
                    'update_source': self.lo_interface, # TODO: change templates to access this from node.bgp.lo_interface
                })

        node.bgp.ebgp_neighbors.sort("asn")
        #pprint.pprint(node.bgp.ebgp_neighbors.dump())

        return

class QuaggaCompiler(RouterCompiler):
    """Base Router compiler"""
    lo_interface = "lo0:1"

    def interfaces(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        phy_node = self.anm.overlay.phy.node(node)
        G_ospf = self.anm['ospf']

        super(QuaggaCompiler, self).interfaces(node)
        # OSPF cost
        for interface in node.interfaces:
            ospf_link = G_ospf.edge(interface._edge_id) # find link in OSPF with this ID
#TODO: check finding link if returns cost from r1 -> r2, or r2 -> r1 (directionality)
            if ospf_link:
                interface['ospf_cost'] = ospf_link.cost

        if phy_node.is_router:
            node.interfaces.append(
                    id = self.lo_interface,
                    description = "Loopback for BGP",
                    ip_address = ip_node.loopback,
                    subnet = node.loopback_subnet
                    )

    def ospf(self, node):
        super(QuaggaCompiler, self).ospf(node)

        # add eBGP link subnets
        G_ip = self.anm['ip']
        G_bgp = self.anm['bgp']
        node.ospf.passive_interfaces = []
        
        for link in G_bgp.edges(node, type = "ebgp"):
            nidb_edge = self.nidb.edge(link)
            node.ospf.passive_interfaces.append(
                    id = nidb_edge.id,
                    )

            ip_link = G_ip.edge(link)
            default_ebgp_area = 0
            if not ip_link:
                #TODO: fix this: due to multi edges from router to same switch cluster
                continue
            node.ospf.ospf_links.append(
                    network = ip_link.dst.subnet,
                    area = default_ebgp_area,
                    )

#TODO: Don't render netkit lab topology if no netkit hosts

class IosBaseCompiler(RouterCompiler):
    """Base IOS compiler"""

    lo_interface = "Loopback0"

    def compile(self, node):
        super(IosBaseCompiler, self).compile(node)
        if node in self.anm['isis']:
            self.isis(node)
        
    def interfaces(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")

#TODO: strip out returns from super
        super(IosBaseCompiler, self).interfaces(node)
        # OSPF cost
        G_ospf = self.anm['ospf']
        G_isis = self.anm['isis']
        
        for interface in node.interfaces:
            ospf_link = G_ospf.edge(interface._edge_id) # find link in OSPF with this ID
            if ospf_link:
                interface['ospf_cost'] = ospf_link.cost
            isis_link = G_isis.edge(interface._edge_id) # find link in OSPF with this ID
            if isis_link: # only configure if has ospf interface
                interface['isis'] = True
                isis_node = G_isis.node(node)
                interface['isis_process_id'] = isis_node.process_id  #TODO: should this be from the interface?
                interface['isis_metric'] = isis_link.metric  #TODO: should this be from the interface?

#TODO: update this to new format
        is_isis_node = bool(G_isis.node(node)) # if node is in ISIS graph
        node.interfaces.append(
            id = self.lo_interface,
            description = "Loopback",
            ip_address = ip_node.loopback,
            subnet = loopback_subnet,
            isis = is_isis_node,
            physical = False,
            )

    def bgp(self, node):
        node.bgp.lo_interface = self.lo_interface
        super(IosBaseCompiler, self).bgp(node)


    def isis(self, node):
        #TODO: this needs to go into IOS2 for neatness
        """Sets ISIS links
        """
        G_isis = self.anm['isis']
        isis_node = self.anm['isis'].node(node)
        node.isis.net = isis_node.net
        node.isis.process_id = isis_node.process_id
        node.isis.lo_interface = self.lo_interface
        node.isis.isis_links = []
        for interface in node.interfaces:
            isis_link = G_isis.edge(interface._edge_id) # find link in OSPF with this ID
            if isis_link: # only configure if has ospf interface
                node.isis.isis_links.append(
                        id = interface.id,
                        metric = isis_link.metric,
                        )

class IosClassicCompiler(IosBaseCompiler):
    def compile(self, node):
        super(IosClassicCompiler, self).compile(node)

        phy_node = self.anm.overlay.phy.node(node)
        if phy_node.include_csr:
            node.include_csr = True
        
class Ios2Compiler(IosBaseCompiler):

    def ospf(self, node):
#need to aggregate areas
        super(Ios2Compiler, self).ospf(node)
        G_ospf = self.anm['ospf']

        interfaces_by_area = defaultdict(list)

        for interface in node.interfaces:
            ospf_link = G_ospf.edge(interface._edge_id) # find link in OSPF with this ID
            if ospf_link:
                area = ospf_link.area
                interfaces_by_area[area].append( {
                    'id': interface.id,
                    'cost': ospf_link.cost,
                    'passive': False,
                    }) #TODO: make this use the same parameter format as other appends... (in nidb API)


        router_area = G_ospf.node(node).area
        interfaces_by_area[router_area].append( {
            'id': self.lo_interface,
            'cost': 0,
            'passive': True,
            })


    # and add Loopback with this router's area

        node.ospf.interfaces = dict(interfaces_by_area)# TODO: workaround for limited wrapping depth, make node.ospf.interfaces grouped by area

# Platform compilers
class PlatformCompiler(object):
    """Base Platform Compiler"""
# and set properties in nidb._graph.graph
    def __init__(self, nidb, anm, host):
        self.nidb = nidb
        self.anm = anm
        self.host = host

    @property
    def timestamp(self):
        return self.nidb.timestamp

    def compile(self):
        #TODO: make this abstract
        pass

class JunosphereCompiler(PlatformCompiler):
    """Junosphere Platform Compiler"""
    def interface_ids(self):
        invalid = set([2])
        valid_ids = (x for x in itertools.count(0) if x not in invalid)
        for x in valid_ids:
            yield "ge-0/0/%s" % x

    def compile(self):
        log.info("Compiling Junosphere for %s" % self.host)
        G_phy = self.anm.overlay.phy
        junos_compiler = JunosCompiler(self.nidb, self.anm)
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='junos'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/junos.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (self.host, "junosphere")
            nidb_node.render.dst_file = "%s.conf" % ank.name_folder_safe(phy_node.label)

            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.unit = 0
                edge.id = int_ids.next()

            junos_compiler.compile(nidb_node)

class NetkitCompiler(PlatformCompiler):
    """Netkit Platform Compiler"""
    def interface_ids(self):
        for x in itertools.count(0):
            yield "eth%s" % x

    def compile(self):
        log.info("Compiling Netkit for %s" % self.host)
        G_phy = self.anm.overlay.phy
        quagga_compiler = QuaggaCompiler(self.nidb, self.anm)
#TODO: this should be all l3 devices not just routers
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='quagga'):
            folder_name = naming.network_hostname(phy_node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.base = "templates/quagga"
            nidb_node.render.template = "templates/netkit_startup.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (self.host, "netkit")
            nidb_node.render.base_dst_folder = "rendered/%s/%s/%s" % (self.host, "netkit", folder_name)
            nidb_node.render.dst_file = "%s.startup" % folder_name 

# allocate zebra information
            nidb_node.zebra.password = "1234"
            hostname = folder_name
            if hostname[0] in string.digits:
                hostname = "r" + hostname
            nidb_node.zebra.hostname = hostname # can't have . in quagga hostnames
            nidb_node.ssh.use_key = True #TODO: make this set based on presence of key
            
            # Note this could take external data
            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()
# and allocate tap interface
            nidb_node.tap.id = int_ids.next()

            quagga_compiler.compile(nidb_node)

            #TODO: move these into inherited BGP config
            nidb_node.bgp.debug = True
            static_routes = []
            nidb_node.zebra.static_routes = static_routes

        # and lab.conf
        self.allocate_tap_ips()
        self.lab_topology()

    def allocate_tap_ips(self):
        #TODO: take tap subnet parameter
        lab_topology = self.nidb.topology[self.host] #TODO: also store platform
        from netaddr import IPNetwork
        address_block = IPNetwork("172.16.0.0/16").iter_hosts() #TODO: read this from config
        lab_topology.tap_host = address_block.next()
        lab_topology.tap_vm = address_block.next() # for tunnel host
        for node in sorted(self.nidb.nodes("is_l3device", host = self.host)):
            #TODO: fix sorting order
            #TODO: check this works for switches
            node.tap.ip = address_block.next()
        
    def lab_topology(self):
#TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology[self.host]
        lab_topology.render_template = "templates/netkit_lab_conf.mako"
        lab_topology.render_dst_folder = "rendered/%s/%s" % (self.host, "netkit")
        lab_topology.render_dst_file = "lab.conf" 
        lab_topology.description = "AutoNetkit Lab"
        lab_topology.author = "AutoNetkit"
        lab_topology.web = "www.autonetkit.org"
        host_nodes = list(self.nidb.nodes(host = self.host, platform = "netkit"))
        if not len(host_nodes):
            log.debug("No Netkit hosts for %s" % self.host)
            #TODO: make so can return here 
            #return
# also need collision domains for this host
        cd_nodes = self.nidb.nodes("collision_domain", host = self.host) # add in collision domains for this host (don't have platform)
#TODO: need to allocate cds to a platform
        host_nodes += cd_nodes
        subgraph = self.nidb.subgraph(host_nodes, self.host)

#TODO: sort this numerically, not just by string
        lab_topology.machines = " ".join(alpha_sort(naming.network_hostname(phy_node) 
            for phy_node in subgraph.nodes("is_l3device")))

        G_ip = self.anm['ip']
        lab_topology.config_items = []
        for node in sorted(subgraph.nodes("is_l3device")):
            for edge in node.edges():
                collision_domain = str(G_ip.edge(edge).dst.subnet).replace("/", ".")
                numeric_id = edge.id.replace("eth", "") # netkit lab.conf uses 1 instead of eth1
                lab_topology.config_items.append(
                    device = naming.network_hostname(node),
                    key = numeric_id,
                    value =  collision_domain,
                    )

        lab_topology.tap_ips = []
        for node in subgraph:
            if node.tap:
                lab_topology.tap_ips.append(
                        #TODO: merge the following and previous into a single function
                        device= naming.network_hostname(node),
                        id= node.tap.id.replace("eth", ""), # strip ethx -> x 
                        ip= node.tap.ip,
                        )

        lab_topology.tap_ips.sort("ip")
        lab_topology.config_items.sort("device")

class CiscoCompiler(PlatformCompiler):
    to_memory = settings['Compiler']['Cisco']['to memory']

    """Cisco Platform Compiler"""
    #def __init__(self, nidb, anm, host):
#TODO: setup to remap allocate interface id function here
        #super(CiscoCompiler, self).__init__(nidb, anm, host)

    def interface_ids_ios(self):
        id_pairs = ( (slot, 0) for slot in itertools.count(0)) 
        for (slot, port) in id_pairs:
            #yield "Ethernet%s/%s" % (slot, port)
            yield "FastEthernet%s/%s" % (slot, port)

    def interface_ids_ios2(self):
        id_pairs = ( (slot, port) for (slot, port) in itertools.product(range(17), range(5))) 
        for (slot, port) in id_pairs:
            yield "GigabitEthernet%s/%s/%s/%s" % (0, 0, slot, port)

    def compile(self):
        def edge_id_numeric(edge):
            """ Used for sorting
            assumes format xx_src_dst -> return the xx component"""
            try:
                return int(edge.edge_id.split("_")[0])
            except ValueError:
                return edge.edge_id # not numeric

        G_in = self.anm['input']
        G_in_directed = self.anm['input_directed']
        specified_int_names = G_in.data.specified_int_names

        log.info("Compiling Cisco for %s" % self.host)
        G_phy = self.anm.overlay.phy
        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        now = datetime.now()
        if settings['Compiler']['Cisco']['timestamp']:
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            dst_folder = "rendered/%s_%s/%s" % (self.host, timestamp, "cisco") #TODO: use os.path.join
        else:
            dst_folder = "rendered/%s/%s" % (self.host,"cisco")
#TODO: merge common router code, so end up with three loops: routers, ios routers, ios2 routers
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='ios'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/ios.mako"
            if self.to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios()
            for edge in sorted(self.nidb.edges(nidb_node), key = edge_id_numeric):
                if specified_int_names:
                    directed_edge = G_in_directed.edge(edge)
                    edge.id = directed_edge.name
                else:
                    edge.id = int_ids.next()

            ios_compiler.compile(nidb_node)

        ios2_compiler = Ios2Compiler(self.nidb, self.anm)
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='ios2'):
            nidb_node = self.nidb.node(phy_node)
            #nidb_node.render.base = "templates/ios2"
            #nidb_node.render.base_dst_folder = "rendered/%s/%s/%s" % (self.host, "cisco", folder_name)
            nidb_node.render.template = "templates/ios2/router.conf.mako"
            if self.to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios2()
            for edge in sorted(self.nidb.edges(nidb_node), key = edge_id_numeric):
                if specified_int_names:
                    directed_edge = G_in_directed.edge(edge)
                    edge.id = directed_edge.name
                else:
                    edge.id = int_ids.next()

            ios2_compiler.compile(nidb_node)

        other_nodes = [phy_node for phy_node in G_phy.nodes('is_router', host = self.host)
                if phy_node.syntax not in ("ios", "ios2")]
        for node in other_nodes:
            phy_node = G_phy.node(node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.input_label = phy_node.id # set specifically for now for other variants

class DynagenCompiler(PlatformCompiler):
    """Dynagen Platform Compiler"""
    def interface_ids(self):
        for x in itertools.count(0):
            yield "gigabitethernet0/0/0/%s" % x

    def compile(self):
        log.info("Compiling Dynagen for %s" % self.host)
        G_phy = self.anm.overlay.phy
        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='ios'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/ios.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (self.host, "dynagen")
            nidb_node.render.dst_file = "%s.conf" % ank.name_folder_safe(phy_node.label)

            # Allocate edges
            # assign interfaces
            # Note this could take external data
            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()

            ios_compiler.compile(nidb_node)
