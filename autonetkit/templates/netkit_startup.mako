% for interface in node.interfaces:  
/sbin/ifconfig ${interface.id} ${interface.ip_address} netmask ${interface.subnet.netmask} broadcast ${interface.subnet.broadcast} up
% endfor                                                                                                                             
route del default
/etc/init.d/zebra start
