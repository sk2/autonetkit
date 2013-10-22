# Static route Config generated on ${date}
% if node.ank_cisco_version:
# by ${ank_version} and autonetkit_cisco ${node.ank_cisco_version}
% else:
# by ${ank_version}
% endif
% for route in node.static_routes_v4:
route add -net ${route.network} gw ${route.gw} dev ${route.interface}
%endfor
% for route in node.host_routes_v4:
route add -host ${route.prefix} gw ${route.gw} dev ${route.interface}
%endfor