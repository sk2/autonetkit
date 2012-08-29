hostname ${node}
password ${node.zebra.password}
enable password ${node.zebra.password}      
banner motd file /etc/quagga/motd.txt

log file /var/log/zebra/zebra.log
