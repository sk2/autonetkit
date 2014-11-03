% for i in node.interfaces:
/sbin/ifconfig ${i.id} ${i.ipv4_address} netmask ${i.ipv4_subnet.netmask} broadcast ${i.ipv4_subnet.broadcast} up
% endfor
route del default
/sbin/ifconfig lo 127.0.0.1 up
/etc/init.d/ssh start
/etc/init.d/hostname.sh
% if node.zebra:
/etc/init.d/zebra start
% endif
% if node.ssh.use_key:
chown -R root:root /root
chmod 755 /root
chmod 755 /root/.ssh
chmod 644 /root/.ssh/authorized_keys
% endif
##TODO: make this toggle-able for telnet login
/etc/init.d/inetd restart
echo pts/0 >> /etc/securetty
echo pts/1 >> /etc/securetty
echo pts/2 >> /etc/securetty
echo pts/3 >> /etc/securetty
echo pts/4 >> /etc/securetty
echo pts/5 >> /etc/securetty
echo pts/6 >> /etc/securetty
