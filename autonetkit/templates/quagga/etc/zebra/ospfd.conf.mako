hostname ${node.hostname}
password ${node.zebra.password}   
banner motd file /etc/quagga/motd.txt
!
% for interface in node.interfaces:  
  %if interface.ospf_cost:
  interface ${interface.id}
  #Link to ${interface.description}
  ip ospf cost ${interface.ospf_cost}
  !
  %endif
%endfor
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
