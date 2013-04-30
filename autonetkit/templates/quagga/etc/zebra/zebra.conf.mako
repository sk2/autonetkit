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
## Loopback
interface lo
description local loopback
ip address 127.0.0.1/8
ip address ${node.loopback}/32
!


log file /var/log/zebra/zebra.log
%endif