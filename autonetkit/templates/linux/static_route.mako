# Static route Config generated on ${date}
! by ${version_banner}
% for route in node.static_routes_v4:
route add -net ${route.network} gw ${route.gw} dev ${route.interface}
%endfor
% for route in node.host_routes_v4:
route add -host ${route.prefix} gw ${route.gw} dev ${route.interface}
%endfor