# daemons file
% if node.zebra:
zebra=yes
%else:
zebra=no
%endif
##  
% if node.bgp:
bgpd=yes
%else:
bgpd=no
%endif
##  
% if node.rip:
ripd=yes
%else:
ripd=no
%endif
##  
% if node.ospf6:
ospf6d=yes
%else:
ospf6d=no
%endif
##  
% if node.ospf:
ospfd=yes
%else:
ospfd=no
%endif
##
% if node.ripngd:
ripngd=yes
%else:
ripngd=no
%endif      
