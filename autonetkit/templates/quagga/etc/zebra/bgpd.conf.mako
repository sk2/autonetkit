!
hostname ${node.zebra.hostname}
password ${node.zebra.password}              
banner motd file /etc/quagga/motd.txt
!enable password ${node.zebra.password}
!
% if node.bgp: 
  router bgp ${node.asn}   
  bgp router-id ${node.loopback}
  no synchronization
  redistribute kernel
  redistribute connected  
% for subnet in node.bgp.advertise_subnets:
  network ${subnet.cidr}
% endfor 
! ibgp
% for client in node.bgp.ibgp_rr_clients:   
% if loop.first:
	! ibgp clients
% endif    
	! ${client.neighbor}
    neighbor ${client.loopback} remote-as ${client.neighbor.asn}
    neighbor ${client.loopback} update-source ${node.loopback} 
	neighbor ${client.loopback} route-reflector-client                                                   
    neighbor ${client.loopback} send-community      
% endfor            
% for parent in node.bgp.ibgp_rr_parents:   
% if loop.first:
	! ibgp route reflector servers
% endif    
	! ${parent.neighbor}
    neighbor ${parent.loopback} remote-as ${parent.neighbor.asn}
    neighbor ${parent.loopback} update-source ${node.loopback} 
    neighbor ${parent.loopback} send-community      
% endfor
% for neigh in node.bgp.ibgp_neighbors:      
% if loop.first:
	! ibgp peers
% endif 
	! ${neigh.neighbor}
    neighbor ${neigh.loopback} remote-as ${neigh.neighbor.asn}
    neighbor ${neigh.loopback} update-source ${node.loopback}                                                     
    neighbor ${neigh.loopback} send-community      
% endfor
! ebgp
% for neigh in node.bgp.ebgp_neighbors:      
	! ${neigh.neighbor} 
    neighbor ${neigh.ip} remote-as ${neigh.neighbor.asn}
    neighbor ${neigh.ip} update-source ${node.loopback}                                                     
    neighbor ${neigh.ip} send-community
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
