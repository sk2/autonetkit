router ${node}
% for data in node.interfaces:
% if loop.first:
	interfaces {
% endif
    ${interface(data)}
% if loop.last:
}
% endif
% endfor

<%def name="interface(data)" filter="trim">
    interface ${data.id} {
    unit ${data.unit} {
	    description "${data.description}";
	    family inet  {
	        address ${data.ip_address}/${data.subnet.prefixlen}
	    }
	    }
	}
</%def>