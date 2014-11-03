##Merged by AutoNetkit merge_quagga_conf on 20140115_162237
% if node.zebra:
hostname ${node.hostname}
password ${node.zebra.password}
enable password ${node.zebra.password}
banner motd file /etc/quagga/motd.txt
% for static_route in node.zebra.static_routes:
! ${static_route.description}
ip route ${static_route.loopback} ${static_route.next_hop}
%endfor
!
% for interface in node.interfaces:
interface ${interface.id}
  %if interface.ospf_cost:
  #Link to ${interface.description}
  ip ospf cost ${interface.ospf_cost}
  !
  %endif
  % if interface.isis:
  ip router isis ${node.isis.process_id}
    % if interface.physical:
  ## level-2-only - why would I want only level 2 network wide?
  isis circuit-type level-2-only
  ## isis metric ${interface.isis_metric}
      % if interface.isis_hello:
  isis hello-interval ${interface.isis_hello}
      % endif
      % if interface.isis_metric:
  isis metric ${interface.isis_metric}
      % endif
    % endif
  % endif
% endfor
## Loopback
interface lo
  description local loopback
  ip address 127.0.0.1/8
  ip address ${node.loopback}/32
!
%endif
% if node.bgp:
router bgp ${node.asn}
  bgp router-id ${node.loopback}
  no synchronization
% for subnet in node.bgp.ipv4_advertise_subnets:
  network ${subnet.cidr}
% endfor
! ibgp
% for client in node.bgp.ibgp_rr_clients:
% if loop.first:
  ! ibgp clients
% endif
  ! ${client.neighbor}
  neighbor ${client.loopback} remote-as ${node.asn}
  neighbor ${client.loopback} update-source ${node.loopback}
  neighbor ${client.loopback} route-reflector-client
  neighbor ${client.loopback} send-community
% endfor
% for parent in node.bgp.ibgp_rr_parents:
% if loop.first:
  ! ibgp route reflector servers
% endif
  ! ${parent.neighbor}
  neighbor ${parent.loopback} remote-as ${parent.asn}
  neighbor ${parent.loopback} update-source ${node.loopback}
  neighbor ${parent.loopback} send-community
% endfor
% for neigh in node.bgp.ibgp_neighbors:
% if loop.first:
  ! ibgp peers
% endif
  ! ${neigh.neighbor}
  neighbor ${neigh.loopback} remote-as ${neigh.asn}
  neighbor ${neigh.loopback} update-source ${node.loopback}
  neighbor ${neigh.loopback} send-community
  neighbor ${neigh.loopback} next-hop-self
% endfor
! ebgp
% for neigh in node.bgp.ebgp_neighbors:
  ! ${neigh.neighbor}
  neighbor ${neigh.dst_int_ip} remote-as ${neigh.asn}
  neighbor ${neigh.dst_int_ip} update-source ${neigh.local_int_ip}
  neighbor ${neigh.dst_int_ip} send-community
% endfor
% endif

% if node.bgp.debug:
debug bgp
debug bgp events
debug bgp filters
debug bgp fsm
debug bgp keepalives
debug bgp updates
log file /var/log/zebra/bgpd.log
% endif
!
% if node.ospf:
router ospf
% for ospf_link in node.ospf.ospf_links:
  network ${ospf_link.network.cidr} area ${ospf_link.area}
% endfor
  !
% for passive_interface in node.ospf.passive_interfaces:
  passive-interface ${passive_interface.id}
% endfor
  !
  network ${node.loopback_subnet} area 0
% endif
!
% if node.isis:
router isis ${node.isis.process_id}
  net ${node.isis.net}
  metric-style wide
% endif
!
log file /var/log/zebra/zebra.log
