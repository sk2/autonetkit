% for i in node.interfaces:  
/sbin/ifconfig ${i.id} ${i.ip_address} netmask ${i.subnet.netmask} broadcast ${i.subnet.broadcast} up
% endfor                                                                                                                             
route del default
/sbin/ifconfig lo 127.0.0.1 up
/etc/init.d/ssh start
/etc/init.d/hostname.sh 
/etc/init.d/zebra start
% if node.ssh.use_key:
chown -R root:root /root     
chmod 755 /root
chmod 755 /root/.ssh
chmod 644 /root/.ssh/authorized_keys
% endif     
