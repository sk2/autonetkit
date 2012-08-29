import ank
import itertools
import netaddr
import os
import autonetkit.log as log

#TODO: rename compiler to build

#TODO: tidy up the dict to list, and sorting formats

def dot_to_underscore(instring):
    return instring.replace(".", "_")

def dict_to_sorted_list(data, sort_key):
    """Returns values in dict, sorted by sort_key"""
    return sorted(data.values(), key = lambda x: x[sort_key])

def sort_attribute(attribute, sort_key):
    return sorted(attribute,  key = lambda x: x[sort_key])

class RouterCompiler(object):
    """Base Router compiler"""
    def __init__(self, nidb, anm):
        self.nidb = nidb
        self.anm = anm

    def compile(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        node.loopback = ip_node.loopback
        node.interfaces = dict_to_sorted_list(self.interfaces(node), 'id')
        if node in self.anm.overlay.ospf:
            node.ospf.ospf_links = dict_to_sorted_list(self.ospf(node), 'network')

        if node in self.anm.overlay.bgp:
            bgp_data = self.bgp(node)
#TODO: just use lists, sort as needed
            node.bgp.ibgp_rr_clients = dict_to_sorted_list(bgp_data['ibgp_rr_clients'], 'neighbor')
            node.bgp.ibgp_rr_parents = dict_to_sorted_list(bgp_data['ibgp_rr_parents'], 'neighbor')
            node.bgp.ibgp_neighbors = dict_to_sorted_list(bgp_data['ibgp_neighbors'], 'neighbor')
            node.bgp.ebgp_neighbors = dict_to_sorted_list(bgp_data['ebgp_neighbors'], 'neighbor')

    def interfaces(self, node):
        phy_node = self.anm.overlay.phy.node(node)
        G_ip = self.anm.overlay.ip
        interfaces = {}
        for link in phy_node.edges():
            ip_link = G_ip.edge(link)
            nidb_edge = self.nidb.edge(link)
            #TODO: what if multiple ospf costs for this link
            if not ip_link:
                #TODO: fix this
                continue

            subnet =  ip_link.dst.subnet # netmask comes from collision domain on the link
            interfaces[link] = {
                    'id': nidb_edge.id,
                    'description': "%s to %s" % (link.src, link.dst),
                    'ip_address': link.overlay.ip.ip_address,
                    'subnet': subnet,
                    }

        return interfaces

    def ospf(self, node):
        """Returns OSPF links
        Also sets process_id
        """
        G_ospf = self.anm.overlay.ospf
        G_ip = self.anm.overlay.ip
        phy_node = self.anm.overlay.phy.node(node)
        node.ospf.process_id = 1
        node.ospf.lo_interface = "Loopback0"
        ospf_links = {}
        for link in G_ospf.edges(phy_node):
            ip_link = G_ip.edge(link)
            if not ip_link:
                #TODO: fix this: due to multi edges from router to same switch cluster
                continue
            
            ospf_links[link] = {
                'network': ip_link.dst.subnet,
                'area': link.area,
                }
        return ospf_links

    def bgp(self, node):
        phy_node = self.anm.overlay.phy.node(node)
        G_bgp = self.anm.overlay.bgp
        G_ip = self.anm.overlay.ip
        asn = phy_node.asn # easy reference for cleaner code
        node.asn = asn
        node.bgp.advertise_subnets = G_ip.data.asn_blocks[asn]
        
        ibgp_neighbors = {}
        ibgp_rr_clients = {}
        ibgp_rr_parents = {}
        ebgp_neighbors = {}

        for session in G_bgp.edges(phy_node):
            neigh = session.dst
            key = str(neigh) # used to index dict for sorting
            neigh_ip = G_ip.node(neigh)
            if session.type == "ibgp":
                data = {
                    'neighbor': neigh,
                    'loopback': neigh_ip.loopback,
                    'update_source': "loopback 0",
                    }
                if session.direction == 'down':
                    ibgp_rr_clients[key] = data
                elif session.direction == 'up':
                    ibgp_rr_parents[key] = data
                else:
                    ibgp_neighbors[key] = data
            else:
                ebgp_neighbors[key] = {
                    'neighbor': neigh,
                    'loopback': neigh_ip.loopback,
                    'update_source': "loopback 0",
                }

        return {
                'ibgp_rr_clients':  ibgp_rr_clients,
                'ibgp_rr_parents': ibgp_rr_parents,
                'ibgp_neighbors': ibgp_neighbors,
                'ebgp_neighbors': ebgp_neighbors,
                }


class QuaggaCompiler(RouterCompiler):
    """Base Router compiler"""
    def interfaces(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")

        interfaces = super(QuaggaCompiler, self).interfaces(node)
        # OSPF cost
        for link in interfaces:
            if link['ospf']:
                interfaces[link]['ospf_cost'] = link['ospf'].cost

        return interfaces

class IosCompiler(RouterCompiler):
    """Base IOS compiler"""

    def interfaces(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")

#TODO: strip out returns from super
        interfaces = super(IosCompiler, self).interfaces(node)
        # OSPF cost
        for link in interfaces:
            interfaces[link]['ospf_cost'] = link.overlay.ospf.cost

        interfaces['lo0'] = {
            'id': 'lo0',
            'description': "Loopback",
            'ip_address': ip_node.loopback,
            'subnet': loopback_subnet,
            }

        return interfaces

class JunosCompiler(RouterCompiler):
    """Base Junos compiler"""

    def compile(self, node):
        node.interfaces = dict_to_sorted_list(self.interfaces(node), 'id')
        if node in self.anm.overlay.ospf:
            node.ospf.ospf_links = dict_to_sorted_list(self.ospf(node), 'network')
            
        if node in self.anm.overlay.bgp:
            bgp_data = self.bgp(node)
            node.bgp.ebgp_neighbors = dict_to_sorted_list(bgp_data['ebgp_neighbors'], 'neighbor')

    def interfaces(self, node):
        ip_node = self.anm.overlay.ip.node(node)
        loopback_subnet = netaddr.IPNetwork("0.0.0.0/32")

        interfaces = super(JunosCompiler, self).interfaces(node)
        for link in interfaces:
            nidb_link =  self.nidb.edge(link)
            interfaces[link]['unit'] = nidb_link.unit

        interfaces['lo0'] = {
            'id': 'lo0',
            'description': "Loopback",
            'ip_address': ip_node.loopback,
            'subnet': loopback_subnet,
            }

        return interfaces

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
            folder_name = ank.name_folder_safe(phy_node.label)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.base = "templates/quagga"
            nidb_node.render.template = "templates/netkit_startup.mako"
            nidb_node.render.dst_folder = "rendered/%s/%s" % (self.host, "netkit")
            nidb_node.render.base_dst_folder = "rendered/%s/%s/%s" % (self.host, "netkit", folder_name)
            nidb_node.render.dst_file = "%s.startup" % folder_name 

# allocate zebra information
            nidb_node.zebra.password = "1234"
            
            # Allocate edges
            # assign interfaces
            # Note this could take external data
            int_ids = self.interface_ids()
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()
# and allocate tap interface
            nidb_node.tap.id = int_ids.next()

            quagga_compiler.compile(nidb_node)

        # and lab.conf
        self.allocate_tap_ips()
        self.lab_topology()

    def allocate_tap_ips(self):
        #TODO: take tap subnet parameter
        lab_topology = self.nidb.topology[self.host]
        from netaddr import IPNetwork
        address_block = IPNetwork("172.16.0.0/16").iter_hosts()
        lab_topology.tap_host = address_block.next()
        lab_topology.tap_vm = address_block.next() # for tunnel host
        for node in self.nidb.nodes("is_l3device", host = self.host):
            #TODO: check this works for switches
            node.tap.ip = address_block.next()
        
    def lab_topology(self):
        host_nodes = self.nidb.nodes(host = self.host)
#TODO: replace name/label and use attribute from subgraph
        lab_topology = self.nidb.topology[self.host]
        lab_topology.render_template = "templates/netkit_lab_conf.mako"
        lab_topology.render_dst_folder = "rendered/%s/%s" % (self.host, "netkit")
        lab_topology.render_dst_file = "lab.conf" 
        subgraph = self.nidb.subgraph(host_nodes, self.host)
        lab_topology.description = "AutoNetkit Lab"
        lab_topology.author = "AutoNetkit"
        lab_topology.web = "www.autonetkit.org"

        G_ip = self.anm['ip']
        config_items = []
        for node in subgraph.nodes("is_l3device"):
            for edge in node.edges('is_router'):
                collision_domain = "%s.%s" % (G_ip.edge(edge).ip_address, 
                        G_ip.edge(edge).dst.subnet.prefixlen)
                numeric_id = edge.id.replace("eth", "") # netkit lab.conf uses 1 instead of eth1
                config_items.append({
                    'device': ank.name_folder_safe(node.label),
                    'key': numeric_id,
                    'value':  collision_domain,
                    })

        tap_ips = []
        for node in subgraph:
            if node.tap:
                tap_ips.append({
                    'device': ank.name_folder_safe(node.label),
                    'id': node.tap.id,
                    'ip': node.tap.ip,
                    })


#TODO: include ram, etc from here

        lab_topology.config_items = config_items
        lab_topology.tap_ips = sort_attribute(tap_ips, "device")
# taps

class CiscoCompiler(PlatformCompiler):
    """Cisco Platform Compiler"""
    def interface_ids_ios(self):
        id_pairs = ( (slot, port) for (slot, port) in itertools.product(range(17), range(5))) 
        for (slot, port) in id_pairs:
            yield "Ethernet%s/%s" % (slot, port)

    def compile(self):
        log.info("Compiling Cisco for %s" % self.host)
        G_phy = self.anm.overlay.phy
        ios_compiler = IosCompiler(self.nidb, self.anm)
        for phy_node in G_phy.nodes('is_router', host = self.host, syntax='ios'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = "templates/ios.mako"
            nidb_node.render.dst_folder = os.path.join(self.host, self.timestamp)
            nidb_node.render.dst_file = "%s.conf" % ank.name_folder_safe(phy_node.label)

            # Assign interfaces
            int_ids = self.interface_ids_ios()
            for edge in self.nidb.edges(nidb_node):
                edge.id = int_ids.next()

            ios_compiler.compile(nidb_node)

class DynagenCompiler(PlatformCompiler):
    """Dynagen Platform Compiler"""
    def interface_ids(self):
        for x in itertools.count(0):
            yield "gigabitethernet0/0/0/%s" % x

    def compile(self):
        log.info("Compiling Dynagen for %s" % self.host)
        G_phy = self.anm.overlay.phy
        ios_compiler = IosCompiler(self.nidb, self.anm)
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
