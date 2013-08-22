import os
from datetime import datetime
import autonetkit
import autonetkit.config
import autonetkit.log as log
import autonetkit.plugins.naming as naming
from autonetkit.ank import sn_preflen_to_network
from autonetkit.compilers.platform.platform_base import PlatformCompiler
import itertools


from autonetkit.compilers.device.cisco import IosBaseCompiler, IosClassicCompiler, IosXrCompiler, NxOsCompiler, StarOsCompiler

class CiscoCompiler(PlatformCompiler):
    """Platform compiler for Cisco"""

    @staticmethod
    def numeric_to_interface_label_ios(x):
        """Starts at GigabitEthernet0/1 """
        x = x + 1
        return "GigabitEthernet0/%s" % x

    @staticmethod
    def numeric_to_interface_label_ra(x):
        """Starts at Gi0/1
        #TODO: check"""
        x = x + 1
        return "GigabitEthernet%s" % x

    @staticmethod
    def numeric_to_interface_label_nxos(x):
        return "Ethernet2/%s" % (x+1)

    @staticmethod
    def numeric_to_interface_label_ios_xr(x):
        return "GigabitEthernet0/0/0/%s" % x

    @staticmethod
    def numeric_to_interface_label_star_os(x):
        return "ethernet 1/%s" % (x + 10)

    @staticmethod
    def numeric_to_interface_label_linux(x):
        return "eth%s" % x

    @staticmethod
    def loopback_interface_ids():
        for x in itertools.count(100): # start at 100 for secondary
            prefix = IosBaseCompiler.lo_interface_prefix
            yield "%s%s" % (prefix, x)

    @staticmethod
    def interface_ids_ios():
        #TODO: make this skip if in list of allocated ie [interface.name for interface in node]
        for x in itertools.count(0):
            yield "GigabitEthernet0/%s" % x

    @staticmethod
    def interface_ids_csr1000v():
        #TODO: make this skip if in list of allocated ie [interface.name for interface in node]
        for x in itertools.count(0):
            yield "GigabitEthernet%s" % x

    @staticmethod
    def interface_ids_nxos():
        for x in itertools.count(0):
            yield "Ethernet2/%s" % x

    @staticmethod
    def interface_ids_ios_xr():
        for x in itertools.count(0):
            yield "GigabitEthernet0/0/0/%s" % x

    @staticmethod
    def numeric_interface_ids():
        """#TODO: later skip interfaces already taken"""
        for x in itertools.count(0):
            yield x

    def compile(self):
        settings = autonetkit.config.settings
        to_memory = settings['Compiler']['Cisco']['to memory']
#TODO: need to copy across the interface name from edge to the interface
        g_phy = self.anm['phy']
        use_mgmt_interfaces = g_phy.data.mgmt_interfaces_enabled
        if use_mgmt_interfaces:
            log.info("Allocating management interfaces for Cisco")
        else:
            log.info("Not allocating management interfaces for Cisco")

        log.info("Compiling Cisco for %s" % self.host)
        now = datetime.now()
        if settings['Compiler']['Cisco']['timestamp']:
            timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
            dst_folder = os.path.join("rendered", self.host, timestamp, "cisco")
        else:
            dst_folder = os.path.join("rendered", self.host, "cisco")
# TODO: merge common router code, so end up with three loops: routers, ios
# routers, ios_xr routers

        # store autonetkit_cisco version
        from pkg_resources import get_distribution
        ank_cisco_version = get_distribution("autonetkit_cisco").version

        for phy_node in g_phy.nodes('is_l3device', host=self.host):
            loopback_ids = self.loopback_interface_ids()
            # allocate loopbacks to routes (same for all ios variants)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.ank_cisco_version = ank_cisco_version
            nidb_node.indices = phy_node.indices

            for interface in nidb_node.loopback_interfaces:
                if interface != nidb_node.loopback_zero:
                    interface.id = loopback_ids.next()

            # numeric ids
            numeric_int_ids = self.numeric_interface_ids()
            for interface in nidb_node.physical_interfaces:
                phy_numeric_id = phy_node.interface(interface).numeric_id
                if phy_numeric_id is None:
                    #TODO: remove numeric ID code
                    interface.numeric_id = numeric_int_ids.next()
                else:
                    interface.numeric_id = int(phy_numeric_id)

                phy_specified_id = phy_node.interface(interface).specified_id
                if phy_specified_id is not None:
                    interface.id = phy_specified_id

        for phy_node in g_phy.nodes('is_server', host=self.host):
            #TODO: look at server syntax also, same as for routers
            nidb_node = self.nidb.node(phy_node)
            for interface in nidb_node.physical_interfaces:
                interface.id = self.numeric_to_interface_label_linux(interface.numeric_id)
                nidb_node.ip.use_ipv4 = phy_node.use_ipv4
                nidb_node.ip.use_ipv6 = phy_node.use_ipv6
                phy_int = phy_node.interface(interface)

                #TODO: make this part of the base device compiler, which server/router inherits
                if nidb_node.ip.use_ipv4:
                    ipv4_int = phy_int['ipv4']
                    if ipv4_int.is_bound:
                        # interface is connected
                        interface.use_ipv4 = True
                        interface.ipv4_address = ipv4_int.ip_address
                        interface.ipv4_subnet = ipv4_int.subnet
                        interface.ipv4_cidr = sn_preflen_to_network(interface.ipv4_address,
                                interface.ipv4_subnet.prefixlen)
                if nidb_node.ip.use_ipv6:
                    ipv6_int = phy_int['ipv6']
                    if ipv6_int.is_bound:
                        # interface is connected
                        interface.use_ipv6 = True
#TODO: for consistency, make ipv6_cidr
                        interface.ipv6_subnet = ipv6_int.subnet
                        interface.ipv6_address = sn_preflen_to_network(ipv6_int.ip_address,
                                interface.ipv6_subnet.prefixlen)


        ios_compiler = IosClassicCompiler(self.nidb, self.anm)
        ios_nodes = (n for n in g_phy.nodes('is_router', host=self.host)
                if n.syntax in ("ios", "ios_xe"))
        for phy_node in ios_nodes:
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","ios.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            #TODO: write function that assigns interface number excluding those already taken

            # Assign interfaces
            if phy_node.device_subtype == "vios":
                int_ids = self.interface_ids_ios()
                numeric_to_interface_label = self.numeric_to_interface_label_ios
            elif phy_node.device_subtype == "CSR1000v":
                int_ids = self.interface_ids_csr1000v()
                numeric_to_interface_label = self.numeric_to_interface_label_ra
            else:
                # default if no subtype specified
                #TODO: need to set default in the load module
                log.warning("Unexpected subtype %s for %s" % (phy_node.device_subtype, phy_node))
                int_ids = self.interface_ids_ios()
                numeric_to_interface_label = self.numeric_to_interface_label_ios

            if use_mgmt_interfaces:
                mgmt_int_id = int_ids.next()  # 0/0 is used for management ethernet

            for interface in nidb_node.physical_interfaces:
                #TODO: use this code block once for all routers
                if not interface.id:
                    interface.id = numeric_to_interface_label(interface.numeric_id)

            ios_compiler.compile(nidb_node)
            if use_mgmt_interfaces:
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

        try:
            from autonetkit_cisco.compilers.device.cisco import IosXrCompiler
            ios_xr_compiler = IosXrCompiler(self.nidb, self.anm)
        except ImportError:
            ios_xr_compiler = IosXrCompiler(self.nidb, self.anm)

        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='ios_xr'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","ios_xr","router.conf.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_ios_xr()
            for interface in nidb_node.physical_interfaces:
                if not interface.id:
                    interface.id = self.numeric_to_interface_label_ios_xr(interface.numeric_id)

            ios_xr_compiler.compile(nidb_node)

            if use_mgmt_interfaces:
                mgmt_int_id = "mgmteth0/0/CPU0/0"
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

        nxos_compiler = NxOsCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='nx_os'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","nx_os.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_nxos()
            for interface in nidb_node.physical_interfaces:
                if not interface.id:
                    interface.id = self.numeric_to_interface_label_nxos(interface.numeric_id)

            nxos_compiler.compile(nidb_node)
            #TODO: make this work other way around

            if use_mgmt_interfaces:
                mgmt_int_id = "mgmt0"
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id

        staros_compiler = StarOsCompiler(self.nidb, self.anm)
        for phy_node in g_phy.nodes('is_router', host=self.host, syntax='StarOS'):
            nidb_node = self.nidb.node(phy_node)
            nidb_node.render.template = os.path.join("templates","staros.mako")
            if to_memory:
                nidb_node.render.to_memory = True
            else:
                nidb_node.render.dst_folder = dst_folder
                nidb_node.render.dst_file = "%s.conf" % naming.network_hostname(
                    phy_node)

            # Assign interfaces
            int_ids = self.interface_ids_nxos()
            for interface in nidb_node.physical_interfaces:
                if not interface.id:
                    interface.id = self.numeric_to_interface_label_star_os(interface.numeric_id)

            staros_compiler.compile(nidb_node)
            #TODO: make this work other way around

            if use_mgmt_interfaces:
                mgmt_int_id = "ethernet 1/1"
                mgmt_int = nidb_node.add_interface(management = True)
                mgmt_int.id = mgmt_int_id


        other_nodes = [phy_node for phy_node in g_phy.nodes('is_router', host=self.host)
                       if phy_node.syntax not in ("ios", "ios_xr")]
        for node in other_nodes:
            #TODO: check why we need this
            phy_node = g_phy.node(node)
            nidb_node = self.nidb.node(phy_node)
            nidb_node.input_label = phy_node.id  # set specifically for now for other variants

# TODO: use more os.path.join for render folders
# TODO: Split compilers into seperate modules

        if use_mgmt_interfaces:
            self.assign_management_interfaces()

    def assign_management_interfaces(self):
        g_phy = self.anm['phy']
        lab_topology = self.nidb.topology[self.host]
        oob_management_ips = {}

        #TODO: remove this code now allocated externally

        #TODO: make this seperate function
        from netaddr import IPNetwork, IPRange

        mgmt_address_start = g_phy.data.mgmt_address_start
        mgmt_address_end = g_phy.data.mgmt_address_end
        mgmt_prefixlen = int(g_phy.data.mgmt_prefixlen)

        #TODO: need to check if range is insufficient
        mgmt_ips = (IPRange(mgmt_address_start, mgmt_address_end))
        mgmt_ips_iter = iter(mgmt_ips) # to iterate over

        mgmt_address_start_network = IPNetwork(mgmt_address_start) # as /32 for supernet
        mgmt_address_end_network = IPNetwork(mgmt_address_end) # as /32 for supernet
        # retrieve the first supernet, as this is the range requested. subsequent are the subnets
        start_subnet = mgmt_address_start_network.supernet(mgmt_prefixlen)[0] # retrieve first
        end_subnet = mgmt_address_end_network.supernet(mgmt_prefixlen)[0] # retrieve first

        try: # validation
            assert(start_subnet == end_subnet)
            log.debug("Verified: Cisco management subnets match")
        except AssertionError:
            log.warning("Error: Cisco management subnets do not match: %s and %s, using start subnet"
                    % (start_subnet, end_subnet))

        mgmt_subnet = start_subnet
        hosts_to_allocate = sorted(self.nidb.nodes('is_router', host=self.host))
        dhcp_subtypes = {"vios"}
        dhcp_hosts = [h for h in hosts_to_allocate if h.device_subtype in dhcp_subtypes]
        non_dhcp_hosts = [h for h in hosts_to_allocate if h.device_subtype not in dhcp_subtypes]

        try: # validation
            assert(len(mgmt_ips) >= len(non_dhcp_hosts))
            log.debug("Verified: Cisco management IP range is sufficient size %s for %s hosts"
                    % (len(mgmt_ips), len(non_dhcp_hosts)))
        except AssertionError:
            log.warning("Error: Cisco management IP range is insufficient size %s for %s hosts"
                    % (len(mgmt_ips), len(non_dhcp_hosts)))
            # TODO: need to use default range
            return

        for nidb_node in hosts_to_allocate:
            for interface in nidb_node.physical_interfaces:
                if interface.management:
                    interface.description = "OOB Management"
                    interface.physical = True
                    interface.mgmt = True
                    interface.comment = "Configured on launch"
                    if nidb_node.ip.use_ipv4:
                        interface.use_ipv4 = False
                    if nidb_node.use_cdp:
                        interface.use_cdp = True # ensure CDP activated
                    if nidb_node in dhcp_hosts:
                        interface.use_dhcp = True
                        oob_management_ips[str(nidb_node)] = "dhcp"
                    else:
                        ipv4_address = mgmt_ips_iter.next()
                        interface.ipv4_address = ipv4_address
                        interface.ipv4_subnet = mgmt_subnet
                        interface.ipv4_cidr = sn_preflen_to_network(ipv4_address, mgmt_prefixlen)
                        oob_management_ips[str(nidb_node)] = ipv4_address

        lab_topology.oob_management_ips = oob_management_ips

