hostname ${node}
password ${node.zebra.password}
enable password ${node.zebra.password}      
banner motd file /etc/quagga/motd.txt
% for static_route in node.zebra.static_routes:
!ip route 182.16.7.8/32 10.1.0.1 
! ${static_route.description}
ip route ${static_route.loopback} ${static_route.next_hop}
%endfor
!


log file /var/log/zebra/zebra.log
