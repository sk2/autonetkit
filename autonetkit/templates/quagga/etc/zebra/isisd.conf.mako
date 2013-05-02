hostname ${node.hostname}
password ${node.zebra.password}   
!log stdout
% for interface in node.interfaces:  
  % if interface.isis:
interface ${interface.id}
  ip router isis ${node.isis.process_id} 
    % if interface.physical:
  ## level-2-only - why would I want only level 2 network wide?
  isis circuit-type level-2-only
  ## isis metric ${interface.isis_metric}
      % if interface.isis_hello:
  isis hello-interval ${interface.isis_hello}
      % endif
      % if interface.isis_metric:
  isis metric ${interface.isis_metric}
      % endif
    % endif
  % endif
% endfor
!
% if node.isis: 
router isis ${node.isis.process_id}
  net ${node.isis.net}
  metric-style wide
% endif
!
