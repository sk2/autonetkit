LAB_DESCRIPTION="${topology.description}"
LAB_VERSION="${ank_version}"
LAB_AUTHOR="${topology.author}"  
LAB_EMAIL="${topology.email}"
LAB_WEB="${topology.web}"    

machines="${topology.machines}"

% for config_item in topology.config_items:
${config_item.device}[${config_item.key}]=${config_item.value}
%endfor

% for tap in topology.tap_ips:
${tap.device}[${tap.id}]=tap,${topology.tap_host},${tap.ip}
%endfor
