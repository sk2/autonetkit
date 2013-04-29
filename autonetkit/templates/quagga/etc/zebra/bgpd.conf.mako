!
hostname ${node.hostname}
password ${node.zebra.password}              
banner motd file /etc/quagga/motd.txt
!enable password ${node.zebra.password}
!
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
