! IOS Config generated on ${date}
% if node.ank_cisco_version:
! by ${ank_version} and autonetkit_cisco ${node.ank_cisco_version}
% else:
! by ${ank_version}
% endif
!
hostname ${node}
boot-start-marker
boot-end-marker
!
% if node.include_csr:
ip routing
license feature csr
!
!
% endif
no aaa new-model
!
!
ip cef
ipv6 unicast-routing
ipv6 cef
!
!
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
% if node.no_service_config:
no service config
%endif
enable password cisco
% if node.enable_secret:
enable secret 4 ${node.enable_secret}
%endif
ip classless
ip subnet-zero
no ip domain lookup
line vty 0 4
% if node.transport_input_ssh_telnet:
 transport input ssh telnet
%endif
 exec-timeout 720 0
 password cisco
 login
line con 0
 password cisco
!
% if node.use_cdp:
!
cdp run
!
%endif
% if node.use_onepk:
!
username cisco privilege 15 password 0 cisco
!
onep
 transport socket
 start
!
%endif
## VRF
% for vrf in node.vrf.vrfs:
vrf definition ${vrf.vrf}
rd ${vrf.rd}
!
% if node.vrf.use_ipv4:
address-family ipv4
  route-target export ${vrf.route_target}
  route-target import ${vrf.route_target}
exit-address-family
%endif
!
%endfor
!
## Physical Interfaces
% for interface in node.interfaces:
interface ${interface.id}
  description ${interface.description}
  % if interface.comment:
  ! ${interface.comment}
  %endif
  % if interface.vrf:
  vrf forwarding ${interface.vrf}
  %endif
  % if interface.use_ipv4:
      %if interface.use_dhcp:
  ip address dhcp
      %else:
  ip address ${interface.ipv4_address} ${interface.ipv4_subnet.netmask}
    %endif
  %else:
  no ip address
  %endif
  % if interface.use_ipv6:
  ipv6 address ${interface.ipv6_address}
  %endif
  % if interface.use_cdp:
  cdp enable
  %endif
  % if interface.ospf:
    %if interface.ospf.use_ipv4:
      %if not interface.ospf.multipoint:
          ###ip ospf network point-to-point
      %endif
  ip ospf cost ${interface.ospf.cost}
    %endif
    %if interface.ospf.use_ipv6:
      %if not interface.ospf.multipoint:
          ###ipv6 ospf network point-to-point
      %endif
  ipv6 ospf cost ${interface.ospf.cost}
  ipv6 ospf ${interface.ospf.process_id} area ${interface.ospf.area}
    %endif
  %endif
  % if interface.isis:
  % if interface.isis.use_ipv4:
  ip router isis ${node.isis.process_id}
    % if interface.physical:
  isis circuit-type level-2-only
      %if not interface.isis.multipoint:
  isis network point-to-point
    % endif
  isis metric ${interface.isis.metric}
    % endif
  % endif
  % if interface.isis.use_ipv6:
  ipv6 router isis ${node.isis.process_id}
    % if interface.physical:
  isis ipv6 metric ${interface.isis.metric}
    % endif
  % endif
  % if interface.isis.mtu:
  clns mtu ${interface.isis.mtu}
  %endif
  % endif
  % if interface.physical:
  duplex auto
  speed auto
  no shutdown
  %endif
  % if interface.use_mpls:
  mpls ip
  %endif
!
% endfor
!
## OSPF
% if node.ospf:
% if node.ospf.use_ipv4:
router ospf ${node.ospf.process_id}
# Loopback
  network ${node.loopback} 0.0.0.0 area ${node.ospf.loopback_area}
  log-adjacency-changes
  passive-interface ${node.ospf.lo_interface}
% for ospf_link in node.ospf.ospf_links:
  network ${ospf_link.network.network} ${ospf_link.network.hostmask} area ${ospf_link.area}
% endfor
% endif
% if node.ospf.use_ipv6:
router ospfv3 ${node.ospf.process_id}
  router-id ${node.loopback}
  !
  address-family ipv6 unicast
  exit-address-family
% endif
% endif
## ISIS
% if node.isis:
router isis ${node.isis.process_id}
  net ${node.isis.net}
  metric-style wide
% if node.isis.use_ipv6:
  !
  address-family ipv6
    multi-topology
  exit-address-family
% endif
% endif
% if node.eigrp:
router eigrp ${node.eigrp.name}
 !
% if node.eigrp.use_ipv4:
 address-family ipv4 unicast autonomous-system ${node.asn}
  !
  topology base
  exit-af-topology
  % for subnet in node.eigrp.ipv4_networks:
  network ${subnet.network} ${subnet.hostmask}
  % endfor
 exit-address-family
 !
% endif
% if node.eigrp.use_ipv4:
 address-family ipv6 unicast autonomous-system ${node.asn}
  !
  topology base
  exit-af-topology
 exit-address-family
!
% endif
% endif
!
% if node.mpls.enabled:
mpls ldp router-id ${node.mpls.router_id}
%endif
!
## BGP
% if node.bgp:
router bgp ${node.asn}
  bgp router-id ${node.router_id}
  no synchronization
% for subnet in node.bgp.ipv4_advertise_subnets:
  network ${subnet.network} mask ${subnet.netmask}
% endfor
! ibgp
## iBGP Route Reflector Clients
% for client in node.bgp.ibgp_rr_clients:
% if loop.first:
  ! ibgp clients
% endif
  !
  neighbor ${client.loopback} remote-as ${client.asn}
  neighbor ${client.loopback} description rr client ${client.neighbor}
  neighbor ${client.loopback} update-source ${node.bgp.lo_interface}
  neighbor ${client.loopback} route-reflector-client
  % if node.bgp.ebgp_neighbors:
  neighbor ${client.loopback} next-hop-self
  % endif
% endfor
## iBGP Route Reflectors (Parents)
% for parent in node.bgp.ibgp_rr_parents:
% if loop.first:
  ! ibgp route reflector servers
% endif
  !
  neighbor ${parent.loopback} remote-as ${parent.asn}
  neighbor ${parent.loopback} description rr parent ${parent.neighbor}
  neighbor ${parent.loopback} update-source ${node.bgp.lo_interface}
  % if node.bgp.ebgp_neighbors:
  neighbor ${parent.loopback} next-hop-self
  % endif
% endfor
## iBGP peers
% for neigh in node.bgp.ibgp_neighbors:
% if loop.first:
  ! ibgp peers
% endif
  !
  neighbor ${neigh.loopback} remote-as ${neigh.asn}
  neighbor ${neigh.loopback} description iBGP peer ${neigh.neighbor}
  neighbor ${neigh.loopback} update-source ${node.bgp.lo_interface}
  % if node.bgp.ebgp_neighbors:
  neighbor ${neigh.loopback} next-hop-self
  % endif
% endfor
## vpnv4 peers
% for neigh in node.bgp.vpnv4_neighbors:
% if loop.first:
  ! vpnv4 peers
  address-family vpnv4
% endif
    neighbor ${neigh.loopback} activate
  % if neigh.rr_client:
    neighbor ${neigh.loopback} route-reflector-client
  % endif
    neighbor ${neigh.loopback} send-community extended
  % if node.bgp.ebgp_neighbors:
    neighbor ${neigh.loopback} next-hop-self
  % endif
  % if loop.last:
  exit-address-family
  %else:
  % endif
% endfor
!
## eBGP peers
% for neigh in node.bgp.ebgp_neighbors:
% if loop.first:
! ebgp
% endif
  !
  neighbor ${neigh.dst_int_ip} remote-as ${neigh.asn}
  neighbor ${neigh.dst_int_ip} description eBGP to ${neigh.neighbor}
  neighbor ${neigh.dst_int_ip} send-community
  neighbor ${neigh.dst_int_ip} next-hop-self
% if loop.last:
!
% endif
% endfor
## VRFs
% for vrf in node.bgp.vrfs:
% if loop.first:
! vrfs
% endif
  address-family ipv4 vrf ${vrf.vrf}
% for neigh in vrf.vrf_ibgp_neighbors:
  % if loop.first:
  % endif
  % if neigh['use_ipv4']:
    neighbor ${neigh['dst_int_ip']} remote-as ${neigh['asn']}
    neighbor ${neigh['dst_int_ip']} activate
    neighbor ${neigh['dst_int_ip']} as-override
    !
  %endif
% endfor
% for neigh in vrf.vrf_ebgp_neighbors:
  % if loop.first:
  % endif
  % if neigh['use_ipv4']:
    neighbor ${neigh['dst_int_ip']} remote-as ${neigh['asn']}
    neighbor ${neigh['dst_int_ip']} activate
    neighbor ${neigh['dst_int_ip']} as-override
    !
  %endif
% endfor
  exit-address-family
  !
%endfor
!
end
% endif
