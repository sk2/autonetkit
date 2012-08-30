!
hostname ${node}
password ${node.zebra.password}              
banner motd file /etc/quagga/motd.txt
!enable password ${node.zebra.password}
!
% if node.bgp: 
  router bgp ${node.asn}   
  no synchronization
% for subnet in node.bgp.advertise_subnets:
	network ${subnet.network} mask ${subnet.netmask}                                                          
% endfor 
! ibgp
% for client in node.bgp.ibgp_rr_clients:   
% if loop.first:
	! ibgp clients
% endif    
	! ${client.neighbor}
	neighbor remote-as ${client.neighbor.asn}
	neighbor ${client.loopback} update-source ${client.update_source} 
	neighbor ${client.loopback} route-reflector-client                                                   
	neighbor send-community      
% endfor            
% for parent in node.bgp.ibgp_rr_parents:   
% if loop.first:
	! ibgp route reflector servers
% endif    
	! ${parent.neighbor}
	neighbor remote-as ${parent.neighbor.asn}
	neighbor ${parent.loopback} update-source ${parent.update_source} 
	neighbor send-community      
% endfor
% for neigh in node.bgp.ibgp_neighbors:      
% if loop.first:
	! ibgp peers
% endif 
	! ${neigh.neighbor}
	neighbor remote-as ${neigh.neighbor.asn}
	neighbor ${neigh.loopback} update-source ${neigh.update_source}                                                     
	neighbor send-community      
% endfor
! ebgp
% for neigh in node.bgp.ebgp_neighbors:      
	! ${neigh.neighbor} 
	neighbor remote-as ${neigh.neighbor.asn}
	neighbor ${neigh.loopback} update-source ${neigh.update_source}                                                     
	neighbor send-community
% endfor    
% endif 

log file /var/log/zebra/bgpd.log
